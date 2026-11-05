# pixelforge for Godot 4: an AnimatedSprite2D that plays an export (PNG + Aseprite-format JSON).
#
# Every tag (<anim>_<dir>; w is drawn, never flipped) becomes an animation with the export's
# per-frame durations, or retimed for another timing profile (COMBAT.md section 2). The node's
# position is the sprite's pivot pixel (its ground point). Events are emitted as `pf_event`
# when their frame shows; hitboxes, hurtboxes and named points come in node coordinates.
#
#   var knight := PixelforgeSprite.new()
#   knight.texture = load("res://art/knight.png")
#   knight.json_path = "res://art/knight.json"
#   add_child(knight)
#   knight.pf_event.connect(func(e): if e.type == "hit": deal_damage(knight.hitboxes()))
#   knight.play_dir("attack_slash", PixelforgeSprite.facing(velocity))
class_name PixelforgeSprite
extends AnimatedSprite2D

signal pf_event(event: Dictionary)

@export var texture: Texture2D
@export_file("*.json") var json_path: String
## Empty: the recipe's own timing. Otherwise player, enemy, elite or boss.
@export var profile: String = ""

var meta: Dictionary = {}
var pivot := Vector2i(15, 27)


func _ready() -> void:
	texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	if texture and json_path != "":
		load_export(texture, json_path)
	frame_changed.connect(_fire)
	animation_changed.connect(_fire)


func load_export(tex: Texture2D, path: String) -> void:
	var data: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(path))
	meta = data["meta"]["pixelforge"]
	pivot = Vector2i(int(meta["pivot"][0]), int(meta["pivot"][1]))
	var frames := SpriteFrames.new()
	frames.remove_animation("default")
	var all: Array = data["frames"]
	for tag in data["meta"]["frameTags"]:
		var tag_name: String = tag["name"]
		var anim := tag_name.substr(0, tag_name.rfind("_"))
		frames.add_animation(tag_name)
		frames.set_animation_speed(tag_name, 1000.0)  # one "frame" per ms: durations below are ms
		frames.set_animation_loop(tag_name, meta["loop"].get(anim, false) == true)
		var first := int(tag["from"])
		var ms := durations(tag_name, all, first, int(tag["to"]))
		for i in range(first, int(tag["to"]) + 1):
			var r: Dictionary = all[i]["frame"]
			var atlas := AtlasTexture.new()
			atlas.atlas = tex
			atlas.region = Rect2(r["x"], r["y"], r["w"], r["h"])
			frames.add_frame(tag_name, atlas, ms[i - first])
	sprite_frames = frames
	centered = false
	offset = -Vector2(pivot)


## Durations in ms for a tag: the export's, or retimed for `profile`: hold frames scale by
## hold_scale, then the last hold before the hit grows until the tell meets the minimum.
func durations(tag_name: String, all: Array, first: int, last: int) -> Array:
	var out: Array = []
	for i in range(first, last + 1):
		out.append(float(all[i]["duration"]))
	if profile == "" or profile == meta.get("timing_profile", ""):
		return out
	var p: Dictionary = meta["timing_profiles"].get(profile, {"hold_scale": 1.0, "telegraph_min_ms": 0})
	var base: Array = meta["base_durations"].get(tag_name, out)
	var holds: Array = meta["holds"].get(tag_name, [])
	out = []
	for i in base.size():
		out.append(float(round(base[i] * p["hold_scale"])) if holds.has(float(i)) or holds.has(i) else float(base[i]))
	var hit := -1
	var start := 0
	var found_windup := false
	for e in meta["events"].get(tag_name, []):
		if (e["type"] == "hit" or e["type"] == "spawn") and (hit < 0 or int(e["frame"]) < hit):
			hit = int(e["frame"])
		if e["type"] == "windup" and (not found_windup or int(e["frame"]) < start):
			start = int(e["frame"])
			found_windup = true
	if hit >= 0 and p["telegraph_min_ms"] > 0:
		var tell := 0.0
		for i in range(start, hit):
			tell += out[i]
		if tell < p["telegraph_min_ms"]:
			var grow := hit - 1
			for h in holds:
				if int(h) >= start and int(h) < hit and (grow == hit - 1 or int(h) > grow):
					grow = int(h)
			out[grow] += p["telegraph_min_ms"] - tell
	return out


func play_dir(anim_name: String, dir: String) -> void:
	var tag := "%s_%s" % [anim_name, dir]
	if animation != tag or not is_playing():
		play(tag)


## The view for a direction of travel or aim: the dominant axis.
static func facing(v: Vector2) -> String:
	if absf(v.x) >= absf(v.y):
		return "e" if v.x >= 0 else "w"
	return "s" if v.y >= 0 else "n"


func _fire() -> void:
	for e in meta.get("events", {}).get(animation, []):
		if int(e["frame"]) == frame:
			pf_event.emit(e)


func _boxes(table: String) -> Array[Rect2]:
	var out: Array[Rect2] = []
	for b in meta.get(table, {}).get(animation, {}).get(str(frame), []):
		out.append(Rect2(b["x"] - pivot.x, b["y"] - pivot.y, b["w"], b["h"]))
	return out


## Damage boxes for the current frame, in node coordinates (only on active frames).
func hitboxes() -> Array[Rect2]:
	return _boxes("hitboxes")


func hurtboxes() -> Array[Rect2]:
	return _boxes("hurtboxes")


## A named point (hand_near, weapon_tip, bow_nock, core...) in node coordinates.
func point(point_name: String) -> Variant:
	var frames: Array = meta.get("points", {}).get(animation, [])
	if frame >= frames.size() or not frames[frame].has(point_name):
		return null
	var p: Array = frames[frame][point_name]
	return Vector2(p[0] - pivot.x, p[1] - pivot.y)
