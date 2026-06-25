"""Object Manager V33 routes."""

import re

from flask import Blueprint, redirect, render_template, request, url_for

try:
    from app.services.object_adapter_engine import (
        ADAPTER_TYPES,
        adapter_from_form,
        adapter_template_name,
    )
    from app.services.object_model import ObjectDefinition
    from app.services import object_registry
    from app.services.object_routing_preview import build_object_routing_preview
except ModuleNotFoundError:
    from services.object_adapter_engine import (
        ADAPTER_TYPES,
        adapter_from_form,
        adapter_template_name,
    )
    from services.object_model import ObjectDefinition
    from services import object_registry
    from services.object_routing_preview import build_object_routing_preview


bp = Blueprint("objects_v33", __name__, template_folder="../../templates")


def _slugify(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "-", text)
    text = text.strip("-_")
    return text or "object"


def _new_object_key(name: str) -> str:
    base = _slugify(name)
    existing = {item.key for item in object_registry.list_objects()}
    if base not in existing:
        return base
    index = 2
    while f"{base}-{index}" in existing:
        index += 1
    return f"{base}-{index}"


def _adapter_protocols(object_def):
    return [
        str(getattr(adapter, "protocol", "") or "").strip().lower()
        for adapter in object_def.adapters
        if getattr(adapter, "enabled", False)
    ]


def _filtered_objects(query: str, active_filter: str = "all"):
    objects = object_registry.list_objects()
    needle = str(query or "").strip().lower()
    active_filter = str(active_filter or "all").strip().lower()
    filtered = [
        item
        for item in objects
        if not needle
        or needle in " ".join(
            [item.id, item.uuid, item.key, item.name, item.category, item.type, item.unit, item.room]
        ).lower()
    ]
    if active_filter == "active":
        return [item for item in filtered if item.enabled]
    if active_filter in ADAPTER_TYPES:
        return [item for item in filtered if active_filter in _adapter_protocols(item)]
    return filtered


def _adapter_map(object_def):
    adapters = {}
    for adapter in object_def.adapters:
        protocol = str(getattr(adapter, "protocol", "") or "").strip().lower()
        if protocol:
            adapters[protocol] = adapter
    return adapters


def _ensure_known_adapters(object_def):
    adapters = _adapter_map(object_def)
    result = []
    for protocol in ("mqtt", "udp", "knx", "loxone", "influx"):
        adapter = adapters.get(protocol)
        if adapter is None:
            adapter = ADAPTER_TYPES[protocol](enabled=False)
        result.append(adapter)
    return result


@bp.route("/objects_v33")
def objects_v33_index():
    query = request.args.get("q", "")
    active_filter = request.args.get("filter", "all")
    objects = _filtered_objects(query, active_filter)
    selected_id = request.args.get("selected", "").strip()
    selected = object_registry.get_object(selected_id) if selected_id else (objects[0] if objects else None)
    return render_template(
        "objects_v33/list.html",
        objects=objects,
        visible_count=len(objects),
        selected=selected,
        selected_adapters=_ensure_known_adapters(selected) if selected else [],
        selected_preview=build_object_routing_preview(selected) if selected else [],
        adapter_template_name=adapter_template_name,
        query=query,
        active_filter=active_filter,
        adapter_protocols=_adapter_protocols,
    )


@bp.route("/objects_v33/new")
def objects_v33_new():
    return render_template(
        "objects_v33/list.html",
        objects=_filtered_objects("", "all"),
        visible_count=len(_filtered_objects("", "all")),
        selected=ObjectDefinition(id=""),
        object_def=ObjectDefinition(id=""),
        selected_adapters=[],
        adapter_template_name=adapter_template_name,
        selected_preview=[],
        query="",
        active_filter="all",
        adapter_protocols=_adapter_protocols,
        errors=[],
        is_new=True,
    )


@bp.route("/objects_v33/edit/<object_uuid>")
def objects_v33_edit(object_uuid):
    object_def = object_registry.get_object(object_uuid)
    if object_def is None:
        return redirect(url_for("objects_v33.objects_v33_index"))
    return redirect(url_for("objects_v33.objects_v33_index", selected=object_def.uuid))


@bp.route("/objects_v33/save", methods=["POST"])
def objects_v33_save():
    object_uuid = request.form.get("uuid", "").strip()
    object_key = request.form.get("key", "").strip()
    name = request.form.get("name", "").strip()
    if not object_key:
        object_key = _new_object_key(name)

    existing = object_registry.get_object(object_uuid) if object_uuid else None
    object_def = ObjectDefinition(
        id=object_key,
        uuid=object_uuid,
        key=object_key,
        name=name,
        category=request.form.get("category", "").strip(),
        type=request.form.get("type", "").strip(),
        unit=request.form.get("unit", "").strip(),
        room=request.form.get("room", "").strip(),
        notes=request.form.get("notes", "").strip(),
        enabled="enabled" in request.form,
        adapters=list(existing.adapters) if existing else [],
    )
    try:
        object_registry.upsert_object(object_def)
    except ValueError as exc:
        return render_template(
            "objects_v33/edit.html",
            object_def=object_def,
            adapters=_ensure_known_adapters(object_def),
            adapter_template_name=adapter_template_name,
            routing_preview=build_object_routing_preview(object_def),
            errors=str(exc).split("; "),
            is_new=False,
        ), 400

    return redirect(url_for("objects_v33.objects_v33_index", selected=object_def.uuid))


@bp.route("/objects_v33/delete/<object_uuid>", methods=["POST"])
def objects_v33_delete(object_uuid):
    object_registry.delete_object(object_uuid)
    return redirect(url_for("objects_v33.objects_v33_index"))


@bp.route("/objects_v33/edit/<object_uuid>/adapter/<protocol>")
def objects_v33_adapter_edit(object_uuid, protocol):
    object_def = object_registry.get_object(object_uuid)
    protocol = str(protocol or "").strip().lower()
    if object_def is None or protocol not in ADAPTER_TYPES:
        return redirect(url_for("objects_v33.objects_v33_index"))
    adapter = _adapter_map(object_def).get(protocol) or ADAPTER_TYPES[protocol](enabled=False)
    return render_template(
        "objects_v33/adapter.html",
        object_def=object_def,
        adapter=adapter,
        adapter_template_name=adapter_template_name,
        errors=[],
    )


@bp.route("/objects_v33/edit/<object_uuid>/adapter/<protocol>/save", methods=["POST"])
def objects_v33_adapter_save(object_uuid, protocol):
    object_def = object_registry.get_object(object_uuid)
    protocol = str(protocol or "").strip().lower()
    if object_def is None or protocol not in ADAPTER_TYPES:
        return redirect(url_for("objects_v33.objects_v33_index"))

    adapter = adapter_from_form(protocol, request.form)
    errors = adapter.validate()
    if errors:
        return render_template(
            "objects_v33/adapter.html",
            object_def=object_def,
            adapter=adapter,
            adapter_template_name=adapter_template_name,
            errors=errors,
        ), 400

    adapters = _adapter_map(object_def)
    adapters[protocol] = adapter
    object_def.adapters = [adapters[item] for item in ("mqtt", "udp", "knx", "loxone", "influx") if item in adapters]
    object_registry.upsert_object(object_def)
    return redirect(url_for("objects_v33.objects_v33_index", selected=object_def.uuid))
