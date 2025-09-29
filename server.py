# -*- coding: utf-8 -*-
"""
Fraytools Animation Importer Server
Created on Fri Mar 14 13:16:31 2025
@author: ZANN
"""

# Standard library imports
import base64
import io
import json
import math
import os
import re
import uuid
import zipfile
from collections import deque, defaultdict

# Third-party imports
import imageio
from PIL import Image, ImageDraw
from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    session,
    current_app,
    send_file,
)
from flask_session import Session


# Flask app configuration
def create_app():
    app = Flask(__name__)

    # App configuration
    app.config.update(
        {
            "MAX_CONTENT_LENGTH": 200 * 1024 * 1024,  # 200MB file upload limit
            "SECRET_KEY": "Ht5y2agdNhajsLkkk",
            "SESSION_TYPE": "filesystem",
            "SESSION_FILE_DIR": os.path.join(app.root_path, "flask_session"),
            "SESSION_PERMANENT": False,
        }
    )

    Session(app)
    return app


app = create_app()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def cap_sentence(s):
    """Capitalize each word in a sentence."""
    return " ".join(w[:1].upper() + w[1:] for w in s.split(" "))


def get_json_data(path: str):
    """Read JSON contents from given path."""
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def generate_sprite_metadata():
    """Generate sprite metadata with a unique GUID."""
    guid = str(uuid.uuid4())

    return {
        "export": False,
        "guid": guid,
        "id": "",
        "pluginMetadata": {},
        "plugins": [],
        "tags": [],
        "version": 2,
    }


# ============================================================================
# DATA PROCESSING FUNCTIONS
# ============================================================================


def get_sprite_data(folder: str):
    """Extract sprite data from the project folder structure."""
    sprite_guids = {}

    def recurse(node):
        for name, content in node.items():
            if name.endswith(".meta") and isinstance(content, dict):
                guid = content["guid"]
                if guid:
                    asset_path = name.replace(".meta", "")
                    asset_data = node.get(asset_path)

                    sprite_guids[guid] = {
                        "path": asset_path,
                        "data": asset_data if isinstance(asset_data, bytes) else None,
                    }

            elif isinstance(content, dict):
                recurse(content)

    recurse(folder)
    return sprite_guids


def convert_to_guid_dict(data_list: list):
    """Convert a list of data objects to a dictionary with GUID as key."""
    return {item["$id"]: item for item in data_list}


# ============================================================================
# SESSION MANAGEMENT
# ============================================================================


def clear_session_data(*keys):
    """Clear specified keys from session data."""
    for key in keys:
        session.pop(key, None)


def initialize_session_data(defaults=None):
    """Initialize session data with default values."""
    defaults = defaults or {}

    if "folder_tree" not in session:
        session["folder_tree"] = defaults.get("folder_tree", {})
        session["file_count"] = defaults.get("file_count", 0)


# ============================================================================
# ROUTE HANDLERS - PAGE ROUTES
# ============================================================================


@app.route("/")
def home():
    """Serve the main HTML page."""
    return render_template("index.html")


@app.route("/frayToGIF")
def fray_to_gif():
    """Serve the GIF conversion page."""
    clear_session_data("folder_tree", "file_count")
    return render_template("frayToGIF.html")


@app.route("/frayAudioStudio")
def fray_audio_studio():
    """Serve the audio studio page."""
    clear_session_data("folder_tree", "file_count")
    return render_template("frayAudioStudio.html")


@app.route("/frayAnimationImporter")
def fray_animation_importer():
    """Serve the animation importer page."""
    clear_session_data("folder_tree", "file_count", "sprite_data")
    return render_template("frayAnimationImporter.html")


# ============================================================================
# ROUTE HANDLERS - API ROUTES
# ============================================================================


def handle_file_upload(files, file_paths, completion_callback):
    """Common file upload handler pattern."""
    initialize_session_data()

    folder_tree = create_folder_structure(files, file_paths, session["folder_tree"])
    session["folder_tree"] = folder_tree
    session["file_count"] += len(files)

    total_files = int(request.form.get("total_files", 0))
    if session["file_count"] == total_files:
        result = completion_callback(folder_tree)
        return jsonify(result), 200

    return jsonify({"status": "Uploading chunk..."}), 200


@app.route("/getAnimationNames", methods=["POST"])
def get_animation_names():
    """Get animation names from uploaded Fraytools project."""
    files = request.files.getlist("files")
    file_paths = request.form.getlist("file_paths")

    def on_completion(folder_tree):
        animation_names = generate_animation_names(folder_tree)
        return {"status": "Upload Complete", "AnimationNames": animation_names}

    return handle_file_upload(files, file_paths, on_completion)


@app.route("/getAudioData", methods=["POST"])
def get_audio_data():
    """Get audio data from uploaded Fraytools project."""
    files = request.files.getlist("files")
    file_paths = request.form.getlist("file_paths")

    def on_completion(folder_tree):
        audio_data = generate_audio_data(folder_tree)
        return {"status": "Upload Complete", "AudioData": audio_data}

    return handle_file_upload(files, file_paths, on_completion)


# ============================================================================
# FOLDER STRUCTURE FUNCTIONS
# ============================================================================


def create_folder_structure(files, file_paths, folder_tree):
    """Create folder structure from uploaded files."""
    for file, path in zip(files, file_paths):
        path_parts = path.split("/")
        current = folder_tree

        # Navigate to the correct folder
        for part in path_parts[:-1]:
            current = current.setdefault(part, {})

        # Process file content based on extension
        content = process_file_content(file)
        current[path_parts[-1]] = content

    return folder_tree


def process_file_content(file):
    """Process file content based on file extension."""
    filename = file.filename.lower()

    if filename.endswith((".entity", ".meta")):
        return json.loads(file.read())
    elif filename.endswith(".png"):
        return file.read()
    elif filename.endswith(".ffe"):
        content = file.read().decode("utf-8")
        session["ffe_data"] = parse_ffe(content)
        return content
    else:
        return file.read()


def create_folder_structure_from_disk(base_folder):
    """Create folder structure from files on disk."""
    folder_tree = {}

    for root, dirs, files in os.walk(base_folder):
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, base_folder)
            path_parts = rel_path.split(os.sep)

            current = folder_tree
            for part in path_parts[:-1]:
                current = current.setdefault(part, {})

            ext = os.path.splitext(filename)[1].lower()
            with open(full_path, "rb") as f:
                content = process_disk_file_content(f, ext)
                if ext == ".ffe":
                    session["ffe_data"] = parse_ffe(content)

            current[path_parts[-1]] = content

    return folder_tree


def process_disk_file_content(file_handle, ext):
    """Process file content from disk based on extension."""
    if ext in (".entity", ".meta", ".json", ".palettes"):
        parsed = json.load(file_handle)
        return {"_type": "json", "_content": parsed}
    elif ext == ".png":
        return file_handle.read()
    elif ext == ".ffe":
        return file_handle.read().decode("utf-8")
    else:
        return file_handle.read()


def generate_animation_names(folder_tree):
    """Extract animation names from folder tree."""
    animation_names = {}

    # Get the first (and typically only) project in the folder tree
    project_key = next(iter(folder_tree))
    entities = folder_tree[project_key]["library"]["entities"]

    for entity_name, entity_data in entities.items():
        animations = entity_data["animations"]
        animation_names[entity_name] = [anim["name"] for anim in animations]

    return animation_names


def generate_audio_data(folder_tree):
    """Extract audio data from folder tree."""
    audio_data = {}
    project_key = next(iter(folder_tree))
    parent_audio = folder_tree[project_key]["library"]["audio"]

    def process_audio_node(node):
        for name, content in node.items():
            if name.endswith(".meta") and isinstance(content, dict):
                guid = content["guid"]
                content_id = content["id"]

                if guid:
                    asset_path = name.replace(".meta", "")
                    asset_data = node.get(asset_path)

                    if isinstance(asset_data, bytes):
                        audio_data[guid] = {
                            "path": asset_path,
                            "id": content_id,
                            "data": base64.b64encode(asset_data).decode("utf-8"),
                        }

            elif isinstance(content, dict):
                process_audio_node(content)

    process_audio_node(parent_audio)
    return audio_data


def generate_sprite_data(sprite_data):
    """Generate metadata for sprite PNG files."""

    def process_sprite_node(node):
        for name, content in list(node.items()):
            if name.endswith(".png"):
                asset_path = name + ".meta"
                sprite_metadata = generate_sprite_metadata()
                node[asset_path] = {"_type": "json", "_content": sprite_metadata}
            elif isinstance(content, dict):
                process_sprite_node(content)

    process_sprite_node(sprite_data)
    return sprite_data


def parse_ffe(text):
    """Parse FFE (Fighter Factory Editor) sprite definition format."""
    blocks = text.strip().split("[SpriteDef]")[1:]
    entries = {}

    for block in blocks:
        # Extract sprite definition parameters using regex
        patterns = {
            "group": r"group\s*=\s*(\d+)",
            "image": r"image\s*=\s*(\d+)",
            "xaxis": r"xaxis\s*=\s*(-?\d+)",
            "yaxis": r"yaxis\s*=\s*(-?\d+)",
            "file": r"file\s*=\s*(.+)",
        }

        matches = {}
        for key, pattern in patterns.items():
            match = re.search(pattern, block)
            if match:
                matches[key] = match.group(1)

        # Create sprite entry if all required fields are present
        if all(key in matches for key in ["group", "image", "xaxis", "yaxis", "file"]):
            sprite_name = f"{matches['group']}-{matches['image']}.png"
            entries[sprite_name] = {
                "file_name": matches["file"],
                "xaxis": int(matches["xaxis"]),
                "yaxis": int(matches["yaxis"]),
            }

    return entries


# ============================================================================
# ROUTE HANDLERS - GIF GENERATION
# ============================================================================


@app.route("/generateGIF", methods=["POST"])
def generate_gif():
    """Generate GIF from animation data."""
    data = request.get_json()

    project_folder = list(session["folder_tree"].keys())[0]
    sprites_folder = session["folder_tree"][project_folder]["library"]["sprites"]
    sprite_guids = get_sprite_data(sprites_folder)

    ce_data = session["folder_tree"][project_folder]["library"]["entities"][
        data["entityName"]
    ]

    result = animation_to_image(data["animationName"], sprite_guids, ce_data)
    return result, 200


# ============================================================================
# ANIMATION PROCESSING FUNCTIONS
# ============================================================================


def build_frame_data(keyframes, symbols, sprite_guids, layer_keyframes):
    """Build frame data from animation layers."""
    master_image = []

    for lk in layer_keyframes:
        keyframe_data = keyframes[lk]
        symbol_data = symbols[keyframe_data["symbol"]]

        for _ in range(keyframe_data["length"]):
            master_image.append(
                [
                    sprite_guids[symbol_data["imageAsset"]]["data"],
                    symbol_data["alpha"],
                    symbol_data["rotation"],
                    symbol_data["scaleX"],
                    symbol_data["scaleY"],
                    symbol_data["x"],
                    symbol_data["y"],
                ]
            )

    return master_image


def calculate_canvas_dimensions(frame_data):
    """Calculate canvas dimensions and positioning from frame data."""
    if not frame_data:
        return 0, 0, 0, 0, 0, 0

    min_x = min_y = max_x = max_y = 0
    positions = []

    for img_info in frame_data:
        img = Image.open(io.BytesIO(img_info[0]))
        img_width, img_height = img.size
        x, y = img_info[5], img_info[6]

        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x + img_width)
        max_y = max(max_y, y + img_height)

        positions.append((x, y))

    canvas_width = max_x - min_x
    canvas_height = max_y - min_y

    minimum_x = min(pos[0] for pos in positions)
    minimum_y = min(pos[1] for pos in positions)

    # Adjust canvas center and dimensions
    if minimum_x < 0:
        canvas_center_x = -minimum_x
    else:
        canvas_width += minimum_x
        canvas_center_x = minimum_x
        min_x -= minimum_x

    if minimum_y < 0:
        canvas_center_y = -minimum_y
    else:
        canvas_height += minimum_y
        canvas_center_y = minimum_y
        min_y -= minimum_y

    return canvas_width, canvas_height, canvas_center_x, canvas_center_y, min_x, min_y


def create_frame_with_crosshair(img_info, canvas_size, canvas_center, min_pos):
    """Create a single frame with crosshair overlay."""
    canvas_width, canvas_height = canvas_size
    canvas_center_x, canvas_center_y = canvas_center
    min_x, min_y = min_pos

    img = Image.open(io.BytesIO(img_info[0]))
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    canvas = Image.new("RGBA", (canvas_width, canvas_height), (56, 52, 52, 255))

    # Draw crosshair
    draw = ImageDraw.Draw(canvas)
    plus_sign_size = 5

    # Vertical line
    draw.line(
        [
            (canvas_center_x, canvas_center_y - plus_sign_size),
            (canvas_center_x, canvas_center_y + plus_sign_size),
        ],
        fill="gray",
        width=1,
    )

    # Horizontal line
    draw.line(
        [
            (canvas_center_x - plus_sign_size, canvas_center_y),
            (canvas_center_x + plus_sign_size, canvas_center_y),
        ],
        fill="gray",
        width=1,
    )

    # Place image
    x, y = img_info[5], img_info[6]
    new_x = x - min_x
    new_y = y - min_y

    canvas.paste(img, (new_x, new_y), mask=img)
    return canvas


def generate_gif_and_webp(frames, duration=1000 // 60):
    """Generate GIF and WebP from frames."""
    if not frames:
        return None, None

    # Generate GIF
    gif_io = io.BytesIO()
    frames[0].save(
        gif_io,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
        transparency=0,
        disposal=2,
    )
    gif_io.seek(0)

    # Generate WebP
    webp_io = io.BytesIO()
    frames[0].save(
        webp_io,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=0,
    )
    webp_io.seek(0)

    return gif_io, webp_io


def animation_to_image(name, sprite_guids, ce_data):
    """Convert animation data to image frames and generate GIF/WebP."""
    animations = ce_data["animations"]

    # Convert lists to GUID-indexed dictionaries for easy lookup
    keyframes = convert_to_guid_dict(ce_data["keyframes"])
    layers = convert_to_guid_dict(ce_data["layers"])
    symbols = convert_to_guid_dict(ce_data["symbols"])

    # Find the target animation
    target_animation = next((a for a in animations if a["name"] == name), None)
    if not target_animation:
        return {"error": f"Animation '{name}' not found"}

    # Process IMAGE layers only
    for layer_id in target_animation["layers"]:
        layer_data = layers[layer_id]

        if layer_data.get("type") == "IMAGE":
            # Build frame data
            frame_data = build_frame_data(
                keyframes, symbols, sprite_guids, layer_data["keyframes"]
            )

            if not frame_data:
                continue

            # Calculate canvas dimensions
            canvas_dims = calculate_canvas_dimensions(frame_data)
            (
                canvas_width,
                canvas_height,
                canvas_center_x,
                canvas_center_y,
                min_x,
                min_y,
            ) = canvas_dims

            # Create frames
            frames = []
            for img_info in frame_data:
                frame = create_frame_with_crosshair(
                    img_info,
                    (canvas_width, canvas_height),
                    (canvas_center_x, canvas_center_y),
                    (min_x, min_y),
                )
                frames.append(frame)

            # Generate output formats
            gif_io, webp_io = generate_gif_and_webp(frames)

            if gif_io and webp_io:
                gif_base64 = base64.b64encode(gif_io.read()).decode("utf-8")
                webp_base64 = base64.b64encode(webp_io.read()).decode("utf-8")

                return {
                    "name": f"{name}.gif",
                    "data": gif_base64,
                    "preview": webp_base64,
                }

    return {"error": "No IMAGE layers found in animation"}


# ============================================================================
# ROUTE HANDLERS - ANIMATION IMPORTER
# ============================================================================


@app.route("/uploadSprites", methods=["POST"])
def upload_sprites():
    """Handle sprite file uploads for animation importing."""
    # Initialize session data
    session_defaults = {
        "folder_tree": {},
        "file_count": 0,
        "sprite_data": {},
        "sprite_name": "",
        "ffe_data": {},
    }

    for key, default in session_defaults.items():
        if key not in session:
            session[key] = default

    files = request.files.getlist("files")
    file_paths = request.form.getlist("file_paths")
    total_files = int(request.form.get("total_files", 0))

    # Process uploaded files
    sprite_data = create_folder_structure(files, file_paths, session["sprite_data"])
    session["sprite_data"] = sprite_data
    session["file_count"] += len(files)

    # Check if all files have been uploaded
    if session["file_count"] == total_files:
        sprite_data = generate_sprite_data(sprite_data)
        session["sprite_data"] = sprite_data
        session["sprite_name"] = list(sprite_data.keys())[0]

        return jsonify({"status": "Upload Complete"}), 200

    return jsonify({"status": "Uploading chunk..."}), 200


@app.route("/uploadAir", methods=["POST"])
def upload_air():
    """Handle AIR file upload for MUGEN animation data."""
    if "air_data" not in session:
        session["air_data"] = ""

    air_file = request.files.get("file")
    if not air_file:
        return jsonify({"error": "No AIR file uploaded"}), 400

    air_content = air_file.read()
    air_data = generate_air_animation_names(air_content)

    session["air_data"] = air_data
    anim_names = list(air_data.keys())

    return jsonify({"status": "Upload Complete", "anim names": anim_names}), 200


@app.route("/uploadCns", methods=["POST"])
def upload_cns():
    """Handle CNS file uploads for MUGEN character data."""
    if "cns_data" not in session:
        session["cns_data"] = []

    uploaded_files = request.files.getlist("files")
    if not uploaded_files:
        return jsonify({"error": "No CNS files uploaded"}), 400

    for file in uploaded_files:
        cns_content = file.read().decode("utf-8")
        session["cns_data"].append(cns_content)

    return jsonify({"status": "Upload Complete"}), 200


# ============================================================================
# MUGEN FILE PROCESSING
# ============================================================================


def generate_air_animation_names(air_data):
    """Parse MUGEN AIR file and extract animation data."""
    lines = air_data.decode("utf-8").splitlines()

    i = 0

    ## Notes:
    ## clsn2default and clsn2 = Hurtbox
    ## clsn1 = Hitbox
    ## Sample frame line goes as follows:
    ## 0,0, 0,0, 12
    ## First 0,0 is sprite name so 0-0.png
    ## Seond 0,0 is X and Y axis in engine?
    ## Last number is frame count, so 12 frames

    actions = {}

    current_animation = None
    current_action = None
    default_clsn2 = []
    default_clsn1 = []

    pending_clsn2 = deque()
    pending_clsn1 = deque()

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip comments or empty lines
        if not line or line.startswith(";"):
            if line.startswith(";") and "[Begin Action" in (
                lines[i + 1] if i + 1 < len(lines) else ""
            ):
                # This is the animation name above [Begin Action]
                current_animation = line.lstrip(";").strip()
            i += 1
            continue

        # Start of new action
        if line.lower().startswith("[begin action"):
            match = re.search(r"\[Begin Action (\d+)\]", line, re.IGNORECASE)
            if match:
                current_action = int(match.group(1))
                actions[current_animation or f"Action_{current_action}"] = {
                    "action": current_action,
                    "frames": [],
                }
                default_clsn2 = []
                default_clsn1 = []
                pending_clsn2 = deque()
                pending_clsn1 = deque()
            i += 1
            continue

        # Default hurtboxes
        if line.lower().startswith("clsn2default"):
            count = int(line.split(":")[1].strip())
            default_clsn2 = []
            for _ in range(count):
                i += 1
                coords = re.findall(r"-?\d+", lines[i])
                default_clsn2.append(list(map(int, coords)))
            i += 1
            continue

        # Frame-specific hurtboxes
        if line.lower().startswith("clsn2:"):
            count = int(line.split(":")[1].strip())
            clsn2_list = []
            for _ in range(count):
                i += 1
                coords = re.findall(r"-?\d+", lines[i])
                clsn2_list.append(list(map(int, coords)))
            pending_clsn2.append(clsn2_list)
            i += 1
            continue

        # Frame-specific hitboxes
        if line.lower().startswith("clsn1:"):
            count = int(line.split(":")[1].strip())
            clsn1_list = []
            for _ in range(count):
                i += 1
                coords = re.findall(r"-?\d+", lines[i])
                clsn1_list.append(list(map(int, coords)))
            pending_clsn1.append(clsn1_list)
            i += 1
            continue

        if re.match(r"^\d+,\d+,\s*-?\d+,\s*-?\d+,\s*-?\d+", line):
            parts = [p.strip() for p in re.split(r"[,\s]+", line) if p.strip() != ""]

            # Skip dummy frames like -1,0, 0,0, -1
            if parts[0] == "-1" and parts[4] == "-1":
                # Clear current action so it won't be saved
                print("False Action")
                actions.pop(current_animation or f"Action_{current_action}", None)
                current_animation = None
                current_action = None
                i += 1
                continue

            image = f"{parts[0]}-{parts[1]}.png"
            offset = [int(parts[2]), int(parts[3])]
            duration = int(parts[4]) if int(parts[4]) != -1 else 2

            extra = parts[5:]  # Everything after duration
            flip = None
            scale = [1, 1]
            angle = 0

            float_vals = []

            for val in extra:
                if val == "H" or val == "V" or val == "HV":
                    flip = val
                elif val == "A":
                    continue  # Ignore transparency
                else:
                    try:
                        float_vals.append(float(val))
                    except ValueError:
                        continue

            if len(float_vals) >= 3:
                scale = float_vals[:-1]
                angle = float_vals[-1]
            elif len(float_vals) == 2:
                scale = float_vals

            frame = {
                "image": image,
                "offset": offset,
                "duration": duration,
                "hurtboxes": (
                    pending_clsn2.popleft() if pending_clsn2 else default_clsn2
                ),
                "hitboxes": pending_clsn1.popleft() if pending_clsn1 else default_clsn1,
                "flip": flip,
                "scale": scale,
                "angle": angle,
            }

            actions[current_animation or f"Action_{current_action}"]["frames"].append(
                frame
            )
        actions[current_animation or f"Action_{current_action}"][
            "Action Code"
        ] = current_action

        i += 1

    actions = {k: v for k, v in actions.items() if v["frames"]}

    return actions


@app.route("/generateAnimPreview", methods=["POST"])
def generate_animation_preview():
    """Generate animation preview from MUGEN AIR data."""
    data = request.get_json()
    anim_name = data["animation"]

    sprite_names = session["sprite_data"][list(session["sprite_data"].keys())[0]]
    frames_data = session["air_data"][anim_name]["frames"]

    def get_canvas_bounds(frames, sprites):
        """Calculate canvas bounds for animation frames."""
        min_x = min_y = max_x = max_y = 0

        for frame in frames:
            img = Image.open(
                io.BytesIO(sprites[session["ffe_data"][frame["image"]]["file_name"]])
            ).convert("RGBA")
            ox, oy = frame["offset"]

            min_x = min(min_x, ox)
            min_y = min(min_y, oy)
            max_x = max(max_x, ox + img.width)
            max_y = max(max_y, oy + img.height)

        return min_x, min_y, max_x, max_y

    # Calculate canvas dimensions
    min_x, min_y, max_x, max_y = get_canvas_bounds(frames_data, sprite_names)
    canvas_width = max_x - min_x
    canvas_height = max_y - min_y

    # Generate frames
    frames = []
    durations = []

    for frame in frames_data:
        img = Image.open(
            io.BytesIO(sprite_names[session["ffe_data"][frame["image"]]["file_name"]])
        ).convert("RGBA")
        ox, oy = frame["offset"]

        # Create canvas and paste image
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        paste_x = ox - min_x
        paste_y = oy - min_y

        alpha_mask = img.getchannel("A")
        canvas.paste(img, (paste_x, paste_y), alpha_mask)

        frames.append(canvas)
        durations.append(frame["duration"] * 10)

    # Generate GIF and WebP
    gif_io, webp_io = generate_gif_and_webp(frames, durations)

    if gif_io and webp_io:
        gif_base64 = base64.b64encode(gif_io.read()).decode("utf-8")
        webp_base64 = base64.b64encode(webp_io.read()).decode("utf-8")
        return {"data": gif_base64, "preview": webp_base64}

    return {"error": "Failed to generate animation preview"}


# ============================================================================
# PROJECT GENERATION FUNCTIONS
# ============================================================================


def add_folder_to_zip(zip_file, folder_tree, current_path=""):
    """Recursively add folder structure to zip file."""
    if current_path:
        zip_file.writestr(current_path + "/", b"")

    for name, content in folder_tree.items():
        path_in_zip = f"{current_path}/{name}" if current_path else name

        if (
            isinstance(content, dict)
            and "_type" in content
            and content["_type"] == "json"
        ):
            json_text = json.dumps(content["_content"], indent=2)
            zip_file.writestr(path_in_zip, json_text.encode("utf-8"))

        elif isinstance(content, dict):
            add_folder_to_zip(zip_file, content, path_in_zip)

        elif isinstance(content, (bytes, str)):
            if isinstance(content, str):
                content = content.encode("utf-8")
            zip_file.writestr(path_in_zip, content)

        elif isinstance(content, (list, int, float, bool)):
            json_text = json.dumps(content, indent=2)
            zip_file.writestr(path_in_zip, json_text.encode("utf-8"))

        else:
            print(f"⚠️ Skipping {path_in_zip}: unsupported type {type(content)}")


def generate_animation(layers, name):
    """Generate animation data structure."""
    animation_guid = str(uuid.uuid4())
    animation_data = {
        "$id": animation_guid,
        "layers": layers,
        "name": name,
        "pluginMetadata": {},
    }
    return animation_guid, animation_data


def generate_layer(keyframes, item_type, hitbox_index=0, hurtbox_index=0):
    """Generate layer data structure."""
    layer_guid = str(uuid.uuid4())

    base_layer = {
        "$id": layer_guid,
        "hidden": False,
        "keyframes": keyframes,
        "locked": False,
    }

    layer_configs = {
        "hurtbox": {
            "defaultAlpha": 0.5,
            "defaultColor": "0xf5e042",
            "name": f"hurtbox{hurtbox_index}",
            "pluginMetadata": {
                "com.fraymakers.FraymakersMetadata": {
                    "collisionBoxType": "HURT_BOX",
                    "index": hurtbox_index,
                }
            },
            "type": "COLLISION_BOX",
        },
        "hitbox": {
            "defaultAlpha": 0.5,
            "defaultColor": "0xff0000",
            "name": f"hitbox{hitbox_index}",
            "pluginMetadata": {
                "com.fraymakers.FraymakersMetadata": {
                    "collisionBoxType": "HIT_BOX",
                    "index": hitbox_index,
                }
            },
            "type": "COLLISION_BOX",
        },
        "image": {
            "name": "Image 0",
            "pluginMetadata": {},
            "type": "IMAGE",
        },
    }

    if item_type not in layer_configs:
        raise ValueError(
            f"Unknown item_type '{item_type}'. Expected one of: {list(layer_configs.keys())}"
        )

    layer_data = {**base_layer, **layer_configs[item_type]}
    return layer_guid, layer_data


def generate_symbol(
    image_asset=None, item_type="IMAGE", x=0, y=0, scaleX=1, scaleY=1, angle=0
):
    """Generate symbol data structure."""
    symbol_guid = str(uuid.uuid4())

    # Base symbol properties
    symbol_data = {
        "$id": symbol_guid,
        "pivotX": 0,
        "pivotY": 0,
        "pluginMetadata": {},
        "rotation": angle,
        "scaleX": scaleX,
        "scaleY": scaleY,
        "x": -x,
        "y": -y,
        "type": item_type,
    }

    if item_type == "IMAGE":
        symbol_data.update(
            {
                "alpha": 1,
                "imageAsset": image_asset,
            }
        )
    elif item_type == "COLLISION_BOX":
        symbol_data.update(
            {
                "alpha": None,
                "color": None,
                "x": -symbol_data["x"],
                "y": -symbol_data["y"],
            }
        )

    return symbol_guid, symbol_data


def generate_keyframe(img_guid, item_type, duration):
    """Generate keyframe data structure."""
    keyframe_guid = str(uuid.uuid4())
    keyframe_data = {
        "$id": keyframe_guid,
        "length": duration,
        "pluginMetadata": {},
        "symbol": img_guid,
        "tweenType": "LINEAR",
        "tweened": False,
        "type": item_type,
    }
    return keyframe_guid, keyframe_data


def add_animations_to_character_entity(ce_file, project_name, state_anim_map):
    """Augment character entity with animations and optional audio frame scripts."""
    air_data = session["air_data"]

    for anim_name, anim_data in air_data.items():
        layers = []
        keyframes = []

        frames = anim_data["frames"]
        hurtbox_count = max((len(f["hurtboxes"]) for f in frames), default=0)
        hitbox_count = max((len(f["hitboxes"]) for f in frames), default=0)

        hurtbox_keyframes = [[] for _ in range(hurtbox_count)]
        hitbox_keyframes = [[] for _ in range(hitbox_count)]

        def append_collision_keyframe(boxes, index_list, frame_duration):
            for i in range(len(index_list)):
                if i < len(boxes):
                    hd = boxes[i]
                    box_guid, symbol_data = generate_symbol(
                        item_type="COLLISION_BOX",
                        x=hd[2],
                        y=hd[3],
                        scaleX=-hd[2] + hd[4],
                        scaleY=-hd[3] + hd[5],
                    )
                    ce_file["symbols"].append(symbol_data)
                else:
                    box_guid = None

                keyframe_guid, keyframe_data = generate_keyframe(
                    box_guid, "COLLISION_BOX", frame_duration
                )
                index_list[i].append(keyframe_guid)
                ce_file["keyframes"].append(keyframe_data)

        for f in frames:
            # Generate image keyframe
            try:
                ffe_data = session["ffe_data"][f["image"]]
                img_meta = session["sprite_data"][session["sprite_name"]][
                    ffe_data["file_name"] + ".meta"
                ]["_content"]

                x = ffe_data["xaxis"]
                y = ffe_data["yaxis"]

                flip = f.get("flip")
                scaleX, scaleY = f.get("scale", [1, 1])
                if flip == "H":
                    scaleX *= -1
                elif flip == "V":
                    scaleY *= -1
                elif flip == "HV":
                    scaleX *= -1
                    scaleY *= -1

                angle = f.get("angle", 0)
                if angle:
                    angle = 360 - angle
                    angle_rad = math.radians(angle)
                    temp_x, temp_y = x, y
                    x = temp_x * math.cos(angle_rad) - temp_y * math.sin(angle_rad)
                    y = temp_x * math.sin(angle_rad) + temp_y * math.cos(angle_rad)

                img_guid, symbol_data = generate_symbol(
                    image_asset=img_meta["guid"],
                    item_type="IMAGE",
                    x=x * scaleX,
                    y=y * scaleY,
                    scaleX=scaleX,
                    scaleY=scaleY,
                    angle=angle,
                )
            except KeyError:
                # Fallback: blank image symbol
                img_guid, symbol_data = generate_symbol(
                    image_asset=None,
                    item_type="IMAGE",
                    x=0,
                    y=0,
                    scaleX=1,
                    scaleY=1,
                    angle=0,
                )

            ce_file["symbols"].append(symbol_data)

            keyframe_guid, keyframe_data = generate_keyframe(
                img_guid, "IMAGE", f["duration"]
            )
            keyframes.append(keyframe_guid)
            ce_file["keyframes"].append(keyframe_data)

            # Append hurtbox and hitbox keyframes
            append_collision_keyframe(f["hurtboxes"], hurtbox_keyframes, f["duration"])
            append_collision_keyframe(f["hitboxes"], hitbox_keyframes, f["duration"])

        # Generate and append all layers
        def create_layer(kf, itype, index=None, audio_data=None):
            if itype == "frame_script" and audio_data:
                layer_guid = str(uuid.uuid4())
                layer_data = {
                    "$id": layer_guid,
                    "hidden": False,
                    "keyframes": kf,
                    "language": "hscript",
                    "locked": False,
                    "name": "Frame Script Layer",
                    "pluginMetadata": {},
                    "type": "FRAME_SCRIPT",
                }
                ce_file["layers"].append(layer_data)
                layers.append(layer_guid)
                return layer_guid, layer_data

            layer_guid, layer_data = generate_layer(
                keyframes=kf,
                item_type=itype,
                hurtbox_index=index if itype == "hurtbox" else None,
                hitbox_index=index if itype == "hitbox" else None,
            )
            ce_file["layers"].append(layer_data)
            layers.append(layer_guid)
            return layer_guid, layer_data

        def create_audio_keyframes(audio_events):
            audio_events = sorted(audio_events, key=lambda x: x["frame"])
            keyframes = []
            for i, event in enumerate(audio_events):
                frame = event["frame"]
                same_frame_events = [e for e in audio_events if e["frame"] == frame]
                code_lines = [f"aud('{e['audio_path']}');" for e in same_frame_events]
                code = "\n".join(code_lines)

                if i + 1 < len(audio_events):
                    next_frame = audio_events[i + 1]["frame"]
                    length = next_frame - frame
                else:
                    length = 1

                kf_id = str(uuid.uuid4())
                keyframe = {
                    "$id": kf_id,
                    "code": code,
                    "length": length,
                    "pluginMetadata": {},
                    "type": "FRAME_SCRIPT",
                }
                ce_file["keyframes"].append(keyframe)
                keyframes.append(kf_id)
            return keyframes

        create_layer(keyframes, "image")
        for i, kfs in enumerate(hurtbox_keyframes):
            create_layer(kfs, "hurtbox", i)
        for i, kfs in enumerate(hitbox_keyframes):
            create_layer(kfs, "hitbox", i)

        action_id = anim_data.get("action")
        if action_id == 220 and action_id in state_anim_map:
            audio_data = state_anim_map[action_id]
            kf_ids = create_audio_keyframes(audio_data)
            create_layer(kf_ids, "frame_script", audio_data=audio_data)

        animation_guid, animation_data = generate_animation(layers, anim_name)
        ce_file["animations"].append(animation_data)

    ce_file["id"] = project_name
    return ce_file


def update_scripts(scripts, project_name):
    """Update script files with the new project name."""
    for script_name in scripts:
        if ".meta" in script_name:
            file_name = script_name.split(".")[0]
            scripts[script_name]["_content"]["id"] = project_name + file_name
        elif script_name == "CharacterStats.hx":
            updated = re.sub(
                b'(?<=self\\.getResource\\(\\)\\.getContent\\(")(.*?)(?=")',
                project_name.encode("utf-8"),
                scripts[script_name],
            )
            scripts[script_name] = updated
    return scripts


def update_manifest(manifest, project_name):
    """Update the manifest with the new project name."""
    manifest["resourceId"] = project_name

    # Update main content
    content_updates = {
        "id": project_name,
        "name": project_name,
        "description": f"{project_name} was imported by the Fraytools Animation Importer by Zardy Z",
        "objectStatsId": f"{project_name}CharacterStats",
        "animationStatsId": f"{project_name}AnimationStats",
        "hitboxStatsId": f"{project_name}HitboxStats",
        "scriptId": f"{project_name}Script",
        "costumesId": f"{project_name}Costumes",
        "aiId": f"{project_name}Ai",
    }

    for key, value in content_updates.items():
        if key in manifest["content"][0]:
            manifest["content"][0][key] = value

    # Update AI code section
    ai_code = manifest["content"][1]
    ai_code["id"] = f"{project_name}Ai"
    ai_code["scriptId"] = f"{project_name}Ai"
    manifest["content"][1] = ai_code

    return manifest


def update_costumes(costumes, project_name):
    """Update the costume.palettes file with the new project name."""
    costumes["id"] = f"{project_name}Costumes"
    return costumes


def parse_sounds_by_state(cns_text):
    data = defaultdict(list)  # {statedef: [all sounds/hits entries]}

    current_statedef = None
    current_section = None
    inside_hitdef = False
    hitdef_data = {}
    current_sound = None
    hitdef_frame = None  # New: store AnimElem frame for HitDef

    lines = cns_text.splitlines()

    re_statedef = re.compile(r"\[Statedef\s+(\d+)\]", re.IGNORECASE)
    re_state = re.compile(r"\[State\s+(\d+),?.*?\]", re.IGNORECASE)
    re_type = re.compile(r"type\s*=\s*(\w+)", re.IGNORECASE)
    re_trigger_anim = re.compile(r"trigger1\s*=\s*AnimElem\s*=\s*(\d+)", re.IGNORECASE)
    re_value = re.compile(r"value\s*=\s*([\d\s,]+)", re.IGNORECASE)
    re_hitsound = re.compile(r"hitsound\s*=\s*(s?.*)", re.IGNORECASE)
    re_guardsound = re.compile(r"guardsound\s*=\s*(s?.*)", re.IGNORECASE)

    for line in lines:
        line = line.strip()
        if not line or line.startswith(";"):
            continue

        # Detect Statedef block
        m_statedef = re_statedef.match(line)
        if m_statedef:
            # Finalize hitdef sounds if we were inside one
            if inside_hitdef and current_statedef is not None:
                if hitdef_data.get("hitsound"):
                    data[current_statedef].append(
                        {
                            "frame": hitdef_frame,
                            "audio_path": hitdef_data["hitsound"],
                            "type": "hit",
                        }
                    )
                if hitdef_data.get("guardsound"):
                    data[current_statedef].append(
                        {
                            "frame": hitdef_frame,
                            "audio_path": hitdef_data["guardsound"],
                            "type": "guard",
                        }
                    )
                inside_hitdef = False
                hitdef_data = {}
                hitdef_frame = None

            current_statedef = int(m_statedef.group(1))
            current_section = None
            current_sound = None
            continue

        # Detect State block
        m_state = re_state.match(line)
        if m_state:
            # Finalize hitdef sounds if we were inside one
            if inside_hitdef and current_statedef is not None:
                if hitdef_data.get("hitsound"):
                    data[current_statedef].append(
                        {
                            "frame": hitdef_frame,
                            "audio_path": hitdef_data["hitsound"],
                            "type": "hit",
                        }
                    )
                if hitdef_data.get("guardsound"):
                    data[current_statedef].append(
                        {
                            "frame": hitdef_frame,
                            "audio_path": hitdef_data["guardsound"],
                            "type": "guard",
                        }
                    )
                inside_hitdef = False
                hitdef_data = {}
                hitdef_frame = None

            current_section = None
            current_sound = None
            continue

        # Detect section type
        m_type = re_type.match(line)
        if m_type:
            t = m_type.group(1).lower()
            current_section = t
            if t in ("playsnd", "playsound"):
                current_sound = {"type": t, "frame": None, "audio_path": None}
                inside_hitdef = False
                hitdef_frame = None
            elif t == "hitdef":
                inside_hitdef = True
                hitdef_data = {"hitsound": None, "guardsound": None}
                hitdef_frame = None
                current_sound = None
            else:
                inside_hitdef = False
                current_sound = None
                hitdef_frame = None
            continue

        # Parse playsnd sound data
        if current_section in ("playsnd", "playsound") and current_sound is not None:
            m_trigger = re_trigger_anim.match(line)
            if m_trigger:
                current_sound["frame"] = int(m_trigger.group(1))
                continue

            m_value = re_value.match(line)
            if m_value:
                audio_vals = m_value.group(1).strip().replace(" ", "").replace(",", "-")
                current_sound["audio_path"] = audio_vals
                if (
                    current_sound["frame"] is not None
                    and current_sound["audio_path"] is not None
                ):
                    if current_statedef is not None:
                        data[current_statedef].append(current_sound)
                    current_sound = None
                continue

        # Parse HitDef block for hitsound, guardsound, and trigger1 AnimElem frame
        if inside_hitdef and current_statedef is not None:
            m_trigger = re_trigger_anim.match(line)
            if m_trigger:
                hitdef_frame = int(m_trigger.group(1))
                continue

            m_hit = re_hitsound.match(line)
            if m_hit:
                val = m_hit.group(1).strip()
                if val.lower().startswith("s"):
                    val = val[1:]
                parts = [p.strip() for p in val.split(",")]
                if len(parts) == 2:
                    val = f"{parts[0]}-{parts[1]}"
                hitdef_data["hitsound"] = val

            m_guard = re_guardsound.match(line)
            if m_guard:
                val = m_guard.group(1).strip()
                if val.lower().startswith("s"):
                    val = val[1:]
                parts = [p.strip() for p in val.split(",")]
                if len(parts) == 2:
                    val = f"{parts[0]}-{parts[1]}"
                hitdef_data["guardsound"] = val

    # Finalize hitdef sounds at EOF if still open
    if inside_hitdef and current_statedef is not None:
        if hitdef_data.get("hitsound"):
            data[current_statedef].append(
                {
                    "frame": hitdef_frame,
                    "audio_path": hitdef_data["hitsound"].replace("s", ""),
                    "type": "hit",
                }
            )
        if hitdef_data.get("guardsound"):
            data[current_statedef].append(
                {
                    "frame": hitdef_frame,
                    "audio_path": hitdef_data["guardsound"].replace("s", ""),
                    "type": "guard",
                }
            )

    return dict(data)


@app.route("/importCharacter", methods=["POST"])
def import_character():
    """Import character data and generate downloadable project."""
    try:

        cns_files = session["cns_data"]

        state_anim_map = {}

        for cns_text in cns_files:
            state_anim_map.update(parse_sounds_by_state(cns_text))

        data = request.get_json()
        app_root = current_app.root_path
        project_name = data["projectName"]

        base_folder = "\\fraymakers-templates\\" + data["template"]
        base_folder = app_root + base_folder

        folder_tree = create_folder_structure_from_disk(base_folder)

        # Rename project folder to match project name
        for folder_key in list(folder_tree.keys()):
            if ".fraytools" in folder_key:
                folder_tree[project_name + ".fraytools"] = folder_tree.pop(folder_key)
                break

        # Add sprites from sprite folder to project files
        folder_tree["library"]["sprites"][session["sprite_name"]] = session[
            "sprite_data"
        ][session["sprite_name"]]

        # Process character entity file
        ce_file = folder_tree["library"]["entities"]["character.entity"]["_content"]
        ce_file = add_animations_to_character_entity(
            ce_file, project_name, state_anim_map
        )

        # Update script names with new project_name
        scripts = folder_tree["library"]["scripts"]["Character"]
        scripts = update_scripts(scripts, project_name)

        manifest = folder_tree["library"]["manifest.json"]["_content"]
        manifest = update_manifest(manifest, project_name)

        costumes = folder_tree["library"]["costumes.palettes"]["_content"]
        costumes = update_costumes(costumes, project_name)

        project_folder_tree = {project_name: folder_tree}

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            add_folder_to_zip(zip_file, project_folder_tree)

        zip_buffer.seek(0)

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{project_name}.zip",
        )

    except Exception as e:
        return jsonify({"error": f"Failed to import character: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
