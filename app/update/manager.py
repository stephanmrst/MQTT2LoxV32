"""Sicherer, plattformneutraler ZIP-Updater für MP-Gateway."""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


PRODUCT_NAME = "MP-Gateway"
PERSISTENT_TOP_LEVEL = {
    "config",
    "data",
    "logs",
    "backups",
    "instance",
    ".env",
    ".git",
}
IGNORED_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".DS_Store"}
MAX_ARCHIVE_BYTES = 750 * 1024 * 1024
MAX_MEMBER_BYTES = 250 * 1024 * 1024
MAX_MEMBERS = 25000


class UpdateError(RuntimeError):
    """Fehler, der dem Benutzer verständlich angezeigt werden kann."""


@dataclass
class RuntimeInfo:
    kind: str
    label: str
    app_dir: str
    config_dir: str
    data_dir: str
    backup_dir: str
    service_name: str
    restart_supported: bool
    restart_hint: str


@dataclass
class PackageInfo:
    product: str
    version: str
    minimum_version: str
    schema_version: int
    restart_required: bool
    package_root: str
    member_count: int
    unpacked_bytes: int


class UpdateManager:
    """Prüft, sichert und installiert MP-Gateway-Updatepakete."""

    _lock = threading.RLock()

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[2]
        app_dir = Path(os.environ.get("MP_GATEWAY_APP_DIR") or os.environ.get("MQTT2LOX_APP_ROOT") or project_root)
        config_dir = Path(os.environ.get("MQTT2LOX_CONFIG_DIR") or (app_dir / "config"))
        data_dir = Path(os.environ.get("MQTT2LOX_DATA_DIR") or (app_dir / "data"))
        backup_dir = Path(os.environ.get("MQTT2LOX_BACKUP_DIR") or (app_dir / "backups"))

        self.app_dir = app_dir.resolve()
        self.config_dir = config_dir.resolve()
        self.data_dir = data_dir.resolve()
        self.backup_dir = backup_dir.resolve()
        self.upload_dir = self.data_dir / "updates" / "uploads"
        self.stage_dir = self.data_dir / "updates" / "staging"
        self.status_file = self.data_dir / "updates" / "status.json"
        self.pending_file = self.data_dir / "updates" / "pending.json"
        self.backup_update_dir = self.backup_dir / "updates"
        for folder in (self.upload_dir, self.stage_dir, self.backup_update_dir):
            folder.mkdir(parents=True, exist_ok=True)

    def current_version(self) -> str:
        try:
            return (self.app_dir / "VERSION").read_text(encoding="utf-8").strip() or "0.0.0"
        except OSError:
            return "0.0.0"

    def runtime_info(self) -> RuntimeInfo:
        service_name = os.environ.get("MP_GATEWAY_SERVICE", "mp-gateway")
        if self._is_docker():
            kind = "docker"
            label = "Docker"
            restart_supported = True
            restart_hint = "Der Container wird beendet und durch die Docker-Restart-Policy neu gestartet."
        elif self._is_lxc():
            kind = "lxc"
            label = "LXC-Container"
            restart_supported = self._systemd_available()
            restart_hint = (
                f"Der systemd-Dienst {service_name} wird neu gestartet."
                if restart_supported
                else f"Bitte den Dienst {service_name} im LXC-Container manuell neu starten."
            )
        elif self._systemd_available():
            kind = "systemd"
            label = "Debian/Linux mit systemd"
            restart_supported = True
            restart_hint = f"Der systemd-Dienst {service_name} wird neu gestartet."
        else:
            kind = "standalone"
            label = f"Standalone ({platform.system()})"
            restart_supported = False
            restart_hint = "MP-Gateway nach dem Update manuell neu starten."

        return RuntimeInfo(
            kind=kind,
            label=label,
            app_dir=str(self.app_dir),
            config_dir=str(self.config_dir),
            data_dir=str(self.data_dir),
            backup_dir=str(self.backup_dir),
            service_name=service_name,
            restart_supported=restart_supported,
            restart_hint=restart_hint,
        )

    def system_info(self) -> dict[str, Any]:
        runtime = self.runtime_info()
        return {
            "version": self.current_version(),
            "runtime": asdict(runtime),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "architecture": platform.machine(),
            "status": self.read_status(),
            "pending": self.read_pending(),
        }

    def save_upload(self, file_storage: Any) -> Path:
        filename = str(getattr(file_storage, "filename", "") or "").strip()
        if not filename.lower().endswith(".zip"):
            raise UpdateError("Bitte eine ZIP-Datei auswählen.")
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(filename).name)
        target = self.upload_dir / f"{stamp}_{safe_name}"
        file_storage.save(target)
        if not target.exists() or target.stat().st_size == 0:
            target.unlink(missing_ok=True)
            raise UpdateError("Die hochgeladene ZIP-Datei ist leer.")
        if target.stat().st_size > MAX_ARCHIVE_BYTES:
            target.unlink(missing_ok=True)
            raise UpdateError("Das Updatepaket ist zu groß.")
        return target

    def inspect_package(self, archive: Path) -> PackageInfo:
        archive = archive.resolve()
        if not archive.is_file():
            raise UpdateError("Updatepaket wurde nicht gefunden.")
        try:
            with zipfile.ZipFile(archive, "r") as zf:
                members = [item for item in zf.infolist() if not item.is_dir()]
                if not members:
                    raise UpdateError("Das Updatepaket enthält keine Dateien.")
                if len(members) > MAX_MEMBERS:
                    raise UpdateError("Das Updatepaket enthält ungewöhnlich viele Dateien.")

                total = 0
                names: list[str] = []
                for item in members:
                    self._validate_member(item)
                    total += int(item.file_size)
                    if total > MAX_ARCHIVE_BYTES:
                        raise UpdateError("Das entpackte Updatepaket ist zu groß.")
                    names.append(item.filename.rstrip("/"))

                root = self._find_package_root(names)
                version_name = f"{root}/VERSION" if root else "VERSION"
                manifest_name = f"{root}/update_manifest.json" if root else "update_manifest.json"
                version = zf.read(version_name).decode("utf-8-sig").strip()
                if not self._version_tuple(version):
                    raise UpdateError("Die VERSION-Datei enthält keine gültige Versionsnummer.")

                manifest: dict[str, Any] = {}
                if manifest_name in zf.namelist():
                    try:
                        manifest = json.loads(zf.read(manifest_name).decode("utf-8-sig"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise UpdateError(f"update_manifest.json ist ungültig: {exc}") from exc

                product = str(manifest.get("product", PRODUCT_NAME)).strip()
                manifest_version = str(manifest.get("version", version)).strip()
                if product != PRODUCT_NAME:
                    raise UpdateError(f"Falsches Produkt im Updatepaket: {product}")
                if manifest_version != version:
                    raise UpdateError("Versionsnummer in Manifest und VERSION stimmt nicht überein.")
                if not self._contains_required_files(names, root):
                    raise UpdateError("Das ZIP ist kein vollständiges MP-Gateway-Updatepaket.")

                return PackageInfo(
                    product=product,
                    version=version,
                    minimum_version=str(manifest.get("minimum_version", "0.0.0")),
                    schema_version=int(manifest.get("schema_version", 1)),
                    restart_required=bool(manifest.get("restart_required", True)),
                    package_root=root,
                    member_count=len(members),
                    unpacked_bytes=total,
                )
        except zipfile.BadZipFile as exc:
            raise UpdateError("Die Datei ist kein gültiges ZIP-Archiv.") from exc
        except KeyError as exc:
            raise UpdateError("Im Updatepaket fehlt die VERSION-Datei.") from exc

    def validate_upgrade(self, package: PackageInfo) -> None:
        current = self.current_version()
        if self._version_tuple(package.version) <= self._version_tuple(current):
            raise UpdateError(
                f"Das Paket {package.version} ist nicht neuer als die installierte Version {current}."
            )
        minimum = package.minimum_version.strip()
        if minimum and self._version_tuple(current) < self._version_tuple(minimum):
            raise UpdateError(
                f"Für dieses Update ist mindestens Version {minimum} erforderlich; installiert ist {current}."
            )
        if package.schema_version != 1:
            raise UpdateError(f"Nicht unterstützte Update-Schema-Version: {package.schema_version}")
        self._assert_writable(self.app_dir)
        self._assert_writable(self.backup_update_dir)
        self._assert_free_space(package.unpacked_bytes)

    def prepare(self, archive: Path) -> dict[str, Any]:
        package = self.inspect_package(archive)
        self.validate_upgrade(package)
        pending = {
            "archive": str(archive.resolve()),
            "package": asdict(package),
            "checked_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._write_json(self.pending_file, pending)
        self.write_status("ready", f"Update {package.version} wurde geprüft und kann installiert werden.", 0)
        return pending

    def install_pending(self) -> dict[str, Any]:
        with self._lock:
            pending = self.read_pending()
            if not pending:
                raise UpdateError("Es wurde noch kein Updatepaket geprüft.")
            archive = Path(str(pending.get("archive", "")))
            package = self.inspect_package(archive)
            self.validate_upgrade(package)
            old_version = self.current_version()
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_update_dir / f"MP-Gateway_{old_version}_{stamp}.zip"
            work_dir = Path(tempfile.mkdtemp(prefix="mpgateway_update_", dir=self.stage_dir))
            extracted = work_dir / "extracted"
            extracted.mkdir(parents=True, exist_ok=True)

            try:
                self.write_status("installing", "Sicherung der aktuellen Programmversion wird erstellt …", 10)
                self._create_program_backup(backup_path)
                self.write_status("installing", "Updatepaket wird sicher entpackt …", 30)
                self._safe_extract(archive, extracted)
                package_root = extracted / package.package_root if package.package_root else extracted
                self.write_status("installing", "Programmdateien werden aktualisiert …", 55)
                self._replace_program_files(package_root)
                self._write_update_marker(package.version, old_version, backup_path)
                self.write_status("installed", f"Update {package.version} wurde installiert. Neustart erforderlich.", 100)
                result = {
                    "old_version": old_version,
                    "new_version": package.version,
                    "backup": str(backup_path),
                    "restart_required": package.restart_required,
                    "runtime": asdict(self.runtime_info()),
                }
                self.pending_file.unlink(missing_ok=True)
                archive.unlink(missing_ok=True)
                return result
            except Exception as exc:
                self.write_status("rollback", f"Installation fehlgeschlagen, Wiederherstellung läuft: {exc}", 80)
                try:
                    if backup_path.exists():
                        self._restore_program_backup(backup_path)
                    self.write_status("failed", f"Update fehlgeschlagen; Version {old_version} wurde wiederhergestellt: {exc}", 100)
                except Exception as rollback_exc:
                    self.write_status("failed", f"Update und Rollback fehlgeschlagen: {exc}; Rollback: {rollback_exc}", 100)
                if isinstance(exc, UpdateError):
                    raise
                raise UpdateError(str(exc)) from exc
            finally:
                shutil.rmtree(work_dir, ignore_errors=True)

    def request_restart(self) -> dict[str, Any]:
        runtime = self.runtime_info()
        if runtime.kind == "docker":
            def delayed_exit() -> None:
                time.sleep(1.0)
                os._exit(0)
            threading.Thread(target=delayed_exit, daemon=True).start()
            return {"ok": True, "message": "Container-Neustart wurde angefordert."}

        if runtime.kind in {"systemd", "lxc"} and runtime.restart_supported:
            service = runtime.service_name
            try:
                subprocess.Popen(
                    ["systemctl", "restart", service],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return {"ok": True, "message": f"Neustart von {service} wurde angefordert."}
            except OSError as exc:
                raise UpdateError(f"systemd-Neustart konnte nicht gestartet werden: {exc}") from exc

        raise UpdateError(runtime.restart_hint)

    def read_status(self) -> dict[str, Any]:
        return self._read_json(self.status_file, {})

    def read_pending(self) -> dict[str, Any]:
        return self._read_json(self.pending_file, {})

    def write_status(self, state: str, message: str, progress: int) -> None:
        self._write_json(
            self.status_file,
            {
                "state": state,
                "message": message,
                "progress": max(0, min(100, int(progress))),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            },
        )

    def _create_program_backup(self, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
            for path in self._iter_program_files(self.app_dir):
                zf.write(path, path.relative_to(self.app_dir).as_posix())

    def _restore_program_backup(self, backup: Path) -> None:
        self._clear_program_files()
        self._safe_extract(backup, self.app_dir)

    def _replace_program_files(self, package_root: Path) -> None:
        if not (package_root / "VERSION").is_file():
            raise UpdateError("Entpacktes Update besitzt keine VERSION-Datei.")
        self._clear_program_files()
        for source in package_root.iterdir():
            if source.name in PERSISTENT_TOP_LEVEL or source.name in IGNORED_NAMES:
                continue
            target = self.app_dir / source.name
            if source.is_dir():
                shutil.copytree(source, target, dirs_exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

    def _clear_program_files(self) -> None:
        self.app_dir.mkdir(parents=True, exist_ok=True)
        for child in self.app_dir.iterdir():
            if child.name in PERSISTENT_TOP_LEVEL or child.name in IGNORED_NAMES:
                continue
            if child.is_symlink() or child.is_file():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                shutil.rmtree(child)

    def _iter_program_files(self, root: Path):
        for path in root.rglob("*"):
            rel = path.relative_to(root)
            if not rel.parts:
                continue
            if rel.parts[0] in PERSISTENT_TOP_LEVEL:
                continue
            if any(part in IGNORED_NAMES for part in rel.parts):
                continue
            if path.is_file() and not path.is_symlink():
                yield path

    def _safe_extract(self, archive: Path, destination: Path) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        base = destination.resolve()
        with zipfile.ZipFile(archive, "r") as zf:
            for item in zf.infolist():
                self._validate_member(item)
                target = (destination / PurePosixPath(item.filename)).resolve()
                if target != base and base not in target.parents:
                    raise UpdateError(f"Unsicherer Pfad im ZIP: {item.filename}")
                if item.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(item, "r") as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst, length=1024 * 1024)

    def _validate_member(self, item: zipfile.ZipInfo) -> None:
        name = item.filename.replace("\\", "/")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or not name.strip("/"):
            raise UpdateError(f"Unsicherer Pfad im ZIP: {item.filename}")
        if item.file_size > MAX_MEMBER_BYTES:
            raise UpdateError(f"Datei im ZIP ist zu groß: {item.filename}")
        mode = (item.external_attr >> 16) & 0o170000
        if mode == 0o120000:
            raise UpdateError(f"Symbolische Links sind im Updatepaket nicht erlaubt: {item.filename}")

    @staticmethod
    def _find_package_root(names: list[str]) -> str:
        candidates = []
        for name in names:
            if name == "VERSION":
                candidates.append("")
            elif name.endswith("/VERSION"):
                candidates.append(name[: -len("/VERSION")])
        if not candidates:
            raise UpdateError("Im Updatepaket fehlt die VERSION-Datei.")
        candidates.sort(key=lambda value: (value.count("/"), len(value)))
        return candidates[0]

    @staticmethod
    def _contains_required_files(names: list[str], root: str) -> bool:
        prefix = f"{root}/" if root else ""
        required = {f"{prefix}VERSION", f"{prefix}app/__init__.py", f"{prefix}app/main.py"}
        return required.issubset(set(names))

    @staticmethod
    def _version_tuple(value: str) -> tuple[int, ...]:
        match = re.fullmatch(r"\s*(\d+(?:\.\d+){1,3})(?:[-+].*)?\s*", str(value))
        if not match:
            return ()
        return tuple(int(part) for part in match.group(1).split("."))

    def _assert_writable(self, folder: Path) -> None:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            probe = folder / f".update_write_test_{os.getpid()}"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
        except OSError as exc:
            raise UpdateError(f"Keine Schreibrechte für {folder}: {exc}") from exc

    def _assert_free_space(self, unpacked_bytes: int) -> None:
        required = max(100 * 1024 * 1024, unpacked_bytes * 3)
        free = shutil.disk_usage(self.app_dir).free
        if free < required:
            raise UpdateError(
                f"Nicht genügend freier Speicher: benötigt ca. {required // (1024*1024)} MB, frei {free // (1024*1024)} MB."
            )

    def _write_update_marker(self, version: str, previous: str, backup: Path) -> None:
        marker = {
            "version": version,
            "previous_version": previous,
            "installed_at": datetime.now().isoformat(timespec="seconds"),
            "backup": str(backup),
        }
        self._write_json(self.app_dir / ".update-managed.json", marker)

    @staticmethod
    def _read_json(path: Path, default: Any) -> Any:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return default

    @staticmethod
    def _write_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, path)

    @staticmethod
    def _is_docker() -> bool:
        if Path("/.dockerenv").exists():
            return True
        try:
            cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="ignore").lower()
            return "docker" in cgroup or "containerd" in cgroup
        except OSError:
            return False

    @staticmethod
    def _is_lxc() -> bool:
        try:
            environ = Path("/proc/1/environ").read_bytes().decode("utf-8", errors="ignore").lower()
            if "container=lxc" in environ:
                return True
        except OSError:
            pass
        try:
            cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="ignore").lower()
            return "lxc" in cgroup
        except OSError:
            return False

    @staticmethod
    def _systemd_available() -> bool:
        return Path("/run/systemd/system").exists() and shutil.which("systemctl") is not None
