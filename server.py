# -*- coding: utf-8 -*-
"""
Created on Fri Mar 14 13:16:31 2025
@author: ZANN
"""

from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    Response,
    session,
    current_app,
    send_file,
)
from flask_session import Session
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
import json
from bs4 import BeautifulSoup
import os
import imageio
from PIL import Image, ImageDraw
import io
import base64
import uuid
import zipfile
import re
from collections import deque
import math

app = Flask(__name__)

## 100MB File Upload Limit
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

app.secret_key = "Ht5y2agdNhajsLkkk"

app.config["SESSION_TYPE"] = "filesystem"  # or 'redis', 'mongodb', etc.
app.config["SESSION_FILE_DIR"] = os.path.join(app.root_path, "flask_session")
app.config["SESSION_PERMANENT"] = False

Session(app)

"""Fixes capatilization"""


def cap_sentence(s):
    return " ".join(w[:1].upper() + w[1:] for w in s.split(" "))


"""Read JSON contents from given path"""


def getJSONData(path: str):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


## Generate sprite metadata
def generateSpriteMetaData():
    guid = str(uuid.uuid4())

    sprite_metadata = {
        "export": False,
        "guid": guid,
        "id": "",
        "pluginMetadata": {},
        "plugins": [],
        "tags": [],
        "version": 2,
    }

    return sprite_metadata


"""Get the sprite data in the project"""


def getSpriteData(folder: str):
    sprite_guids = {}

    def recurse(node):
        for name, content in node.items():
            # current_path = f"{path}/{name}".strip("/")

            if name.endswith(".meta") and isinstance(content, dict):
                guid = content["guid"]
                if guid:
                    asset_path = name.replace(".meta", "")
                    ##sprite_guids[guid] = asset_path

                    asset_data = node.get(asset_path)
                    if isinstance(asset_data, bytes):
                        sprite_guids[guid] = {"path": asset_path, "data": asset_data}
                    else:
                        # Just store the path if no image data
                        sprite_guids[guid] = {"path": asset_path, "data": None}

            elif isinstance(content, dict):
                recurse(content)

    recurse(folder)

    return sprite_guids


"""Converts data list to a dict with GUID as key"""


def convertToGUID(data_list: list):
    data_dict = {}
    for dl in data_list:
        data_dict[dl["$id"]] = dl

    return data_dict


@app.route("/")
def home():
    return render_template("index.html")  # Serve the HTML page


@app.route("/frayToGIF")
def frayToGIF():
    session.pop("folder_tree", None)
    session.pop("file_count", None)
    return render_template("frayToGIF.html")


@app.route("/frayAudioStudio")
def frayAudioStudio():
    session.pop("folder_tree", None)
    session.pop("file_count", None)
    return render_template("frayAudioStudio.html")


@app.route("/frayAnimationImporter")
def frayAnimationImporter():
    session.pop("folder_tree", None)
    session.pop("file_count", None)
    session.pop("sprite_data", None)
    return render_template("frayAnimationImporter.html")


## Fraytools General Functions
@app.route("/getAnimationNames", methods=["POST"])
def getAnimationNames():

    if "folder_tree" not in session:
        session["folder_tree"] = {}  # Initialize empty tree in session
        session["file_count"] = 0

    files = request.files.getlist("files")
    file_paths = request.form.getlist("file_paths")

    folder_tree = createFolderStructure(files, file_paths, session["folder_tree"])
    session["folder_tree"] = folder_tree
    # print(session['folder_tree'])

    # Increment the file count
    session["file_count"] += len(files)

    if session["file_count"] == int(request.form.get("total_files")):
        animation_names = generateAnimationNames(folder_tree)

        final_dict = {"status": "Upload Complete", "AnimationNames": animation_names}

        # Clear session data after processing
        # session.pop('folder_tree', None)
        # session.pop('file_count', None)

        return jsonify(final_dict), 200

    return jsonify({"status": "Uploading chunk..."}), 200


## Fraytools General Functions
@app.route("/getAudioData", methods=["POST"])
def getAudioData():

    if "folder_tree" not in session:
        session["folder_tree"] = {}  # Initialize empty tree in session
        session["file_count"] = 0

    files = request.files.getlist("files")
    file_paths = request.form.getlist("file_paths")

    folder_tree = createFolderStructure(files, file_paths, session["folder_tree"])
    session["folder_tree"] = folder_tree
    # print(session['folder_tree'])

    # Increment the file count
    session["file_count"] += len(files)

    if session["file_count"] == int(request.form.get("total_files")):

        audio_data = generateAudioData(folder_tree)

        final_dict = {"status": "Upload Complete", "AudioData": audio_data}

        # Clear session data after processing
        # session.pop('folder_tree', None)
        # session.pop('file_count', None)

        return jsonify(final_dict), 200

    return jsonify({"status": "Uploading chunk..."}), 200


def createFolderStructure(files, file_paths, folder_tree):

    for file, path in zip(files, file_paths):

        path_parts = path.split("/")
        current = folder_tree

        for part in path_parts[:-1]:  # Traverse folders
            current = current.setdefault(part, {})
        # Read file content as text (optionally decode if needed)

        if file.filename.endswith(".entity") or file.filename.endswith(".meta"):
            content = json.loads(file.read())
        elif file.filename.endswith(".png"):
            content = file.read()
        elif file.filename.endswith(".ffe"):
            content = file.read().decode("utf-8")
            session["ffe_data"] = parseFFE(content)
        else:
            content = file.read()

        current[path_parts[-1]] = content

    return folder_tree


def createFolderStructureFromDisk(base_folder):
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
                if ext in (".entity", ".meta", ".json", ".palettes"):
                    parsed = json.load(f)
                    content = {"_type": "json", "_content": parsed}
                elif ext == ".png":
                    content = f.read()
                elif ext == ".ffe":
                    text = f.read().decode("utf-8")
                    content = text
                    session["ffe_data"] = parseFFE(text)
                else:
                    content = f.read()

            current[path_parts[-1]] = content

    return folder_tree


def generateAnimationNames(folder_tree):
    animation_names = {}

    for e, v in folder_tree[next(iter(folder_tree))]["library"]["entities"].items():

        animations = v["animations"]

        animation_name_list = []
        for a in animations:
            animation_name_list.append(a["name"])

        animation_names[e] = animation_name_list

    return animation_names


def generateAudioData(folder_tree):
    audio_data = {}
    parent_audio = folder_tree[next(iter(folder_tree))]["library"]["audio"]

    def recurse(node):
        for name, content in node.items():
            # current_path = f"{path}/{name}".strip("/")

            if name.endswith(".meta") and isinstance(content, dict):
                guid = content["guid"]
                content_id = content["id"]
                if guid:
                    asset_path = name.replace(".meta", "")
                    ##sprite_guids[guid] = asset_path

                    asset_data = node.get(asset_path)
                    if isinstance(asset_data, bytes):
                        audio_data[guid] = {
                            "path": asset_path,
                            "id": content_id,
                            "data": base64.b64encode(asset_data).decode("utf-8"),
                        }

            elif isinstance(content, dict):
                recurse(content)

    recurse(parent_audio)

    return audio_data


def generateSpriteData(sprite_data):
    def recurse(node):

        for name, content in list(node.items()):

            if name.endswith(".png"):
                asset_path = name + ".meta"
                sprite_metadata = generateSpriteMetaData()
                node[asset_path] = {"_type": "json", "_content": sprite_metadata}

            elif isinstance(content, dict):
                recurse(content)

    recurse(sprite_data)
    return sprite_data


def parseFFE(text):
    blocks = text.strip().split("[SpriteDef]")[1:]
    print("Blocks")
    print(blocks[0])

    entries = {}

    for block in blocks:
        group = re.search(r"group\s*=\s*(\d+)", block)
        image = re.search(r"image\s*=\s*(\d+)", block)
        xaxis = re.search(r"xaxis\s*=\s*(-?\d+)", block)
        yaxis = re.search(r"yaxis\s*=\s*(-?\d+)", block)
        file_name = re.search(r"file\s*=\s*(.+)", block)

        if group and image and xaxis and yaxis:
            group_val = group.group(1)
            image_val = image.group(1)
            xaxis_val = int(xaxis.group(1))
            yaxis_val = int(yaxis.group(1))
            file_name_val = file_name.group(1)
            sprite_name = f"{group_val}-{image_val}.png"
            entries[sprite_name] = {
                "file_name": file_name_val,
                "xaxis": xaxis_val,
                "yaxis": yaxis_val,
            }

            ## EX:
            ## 5040-20.png = {File Name: 5040-20.png, xaxis: 49, yaxis: 45}

    return entries


@app.route("/generateGIF", methods=["POST"])
def generateGIF():
    data = request.get_json()

    project_folder = list(session["folder_tree"].keys())[0]

    sprites_folder = session["folder_tree"][project_folder]["library"]["sprites"]
    sprite_guids = getSpriteData(sprites_folder)

    ce_data = session["folder_tree"][project_folder]["library"]["entities"][
        data["entityName"]
    ]

    result = animationToImg(data["animationName"], sprite_guids, ce_data)
    return result, 200


def animationToImg(name, sprite_guids, ce_data):

    animations = ce_data["animations"]

    keyframes = ce_data["keyframes"]
    new_keyframes = convertToGUID(keyframes)

    layers = ce_data["layers"]
    new_layers = convertToGUID(layers)

    symbols = ce_data["symbols"]
    new_symbols = convertToGUID(symbols)

    for a in animations:
        if a["name"] == name:
            animation_layers = a["layers"]

            for al in animation_layers:
                layer_data = new_layers[al]
                if al == layer_data["$id"] and layer_data["type"] == "IMAGE":
                    layer_keyframes = layer_data["keyframes"]
                    master_image = []
                    for lk in layer_keyframes:
                        keyframe_data = new_keyframes[lk]
                        # print(keyframe_data)

                        symbol_data = new_symbols[keyframe_data["symbol"]]
                        for x in range(0, keyframe_data["length"]):
                            # print(sprite_guids[symbol_data['imageAsset']]['path'])
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

                    min_x = min_y = 0
                    max_x = max_y = 0

                    x_pos = []
                    y_pos = []

                    for img_info in master_image:
                        # print(img_info[0])
                        img = Image.open(io.BytesIO(img_info[0]))
                        # img = Image.open(img_info[0])
                        img_width, img_height = img.size
                        x, y = (img_info[5], img_info[6])

                        # Track the minimum and maximum coordinates
                        min_x = min(min_x, x)
                        min_y = min(min_y, y)

                        max_x = max(max_x, x + img_width)
                        max_y = max(max_y, y + img_height)

                        x_pos.append(x)
                        y_pos.append(y)

                    canvas_width = max_x - min_x
                    canvas_height = max_y - min_y

                    minimum_x = min(x_pos)
                    minimum_y = min(y_pos)

                    if minimum_x < 0:
                        canvas_center_x = minimum_x * -1
                    else:
                        print("Here")
                        canvas_width += minimum_x
                        canvas_center_x = minimum_x
                        min_x -= minimum_x

                    if minimum_y < 0:
                        canvas_center_y = minimum_y * -1
                    else:
                        canvas_height += minimum_y
                        canvas_center_y = minimum_y
                        min_y -= minimum_y

                    frames = []

                    for img_info in master_image:
                        img = Image.open(io.BytesIO(img_info[0]))

                        canvas = Image.new(
                            "RGBA", (canvas_width, canvas_height), (56, 52, 52, 255)
                        )

                        # Get the position wherse the image should be placed
                        x, y = (img_info[5], img_info[6])

                        draw = ImageDraw.Draw(canvas)
                        plus_sign_size = 5  # Size of the plus sign

                        # Vertical line of the plus sign at the canvas center
                        draw.line(
                            [
                                (canvas_center_x, canvas_center_y - plus_sign_size),
                                (canvas_center_x, canvas_center_y + plus_sign_size),
                            ],
                            fill="gray",
                            width=1,
                        )

                        # Horizontal line of the plus sign at the canvas center
                        draw.line(
                            [
                                (canvas_center_x - plus_sign_size, canvas_center_y),
                                (canvas_center_x + plus_sign_size, canvas_center_y),
                            ],
                            fill="gray",
                            width=1,
                        )

                        # Shift the position to positive coordinates by translating by the minimum X and Y
                        new_x = x - min_x
                        new_y = y - min_y

                        if img.mode != "RGBA":
                            img = img.convert("RGBA")

                        canvas.paste(img, (new_x, new_y), mask=img)

                        frames.append(canvas)

                    # gif_path = name+".gif"
                    gif_io = io.BytesIO()

                    frames[0].save(
                        gif_io,
                        format="GIF",
                        save_all=True,
                        append_images=frames[1:],
                        duration=1000
                        // 60,  # Frame duration in milliseconds (1000 ms / 60 FPS = ~16.67 ms)
                        loop=0,
                        transparency=0,
                        disposal=2,  # Clear the frame before displaying the next
                    )

                    gif_io.seek(0)

                    webp_io = io.BytesIO()
                    frames[0].save(
                        webp_io,
                        format="WEBP",
                        save_all=True,
                        append_images=frames[1:],
                        duration=1000 // 60,
                        loop=0,
                    )
                    webp_io.seek(0)

    webp_base64 = base64.b64encode(webp_io.read()).decode("utf-8")
    gif_base64 = base64.b64encode(gif_io.read()).decode("utf-8")
    return {"name": name + ".gif", "data": gif_base64, "preview": webp_base64}


## Fraytools Animation Importer
@app.route("/uploadSprites", methods=["POST"])
def uploadSprites():

    if "folder_tree" not in session:
        session["folder_tree"] = {}  # Initialize empty tree in session
        session["file_count"] = 0
        session["sprite_data"] = {}
        session["sprite_name"] = ""
        session["ffe_data"] = {}

    files = request.files.getlist("files")
    file_paths = request.form.getlist("file_paths")

    sprite_data = createFolderStructure(files, file_paths, session["sprite_data"])
    session["sprite_data"] = sprite_data

    # Increment the file count
    session["file_count"] += len(files)

    if session["file_count"] == int(request.form.get("total_files")):
        ffe_data = {}
        sprite_data = generateSpriteData(sprite_data)

        session["sprite_data"] = sprite_data
        session["sprite_name"] = list(sprite_data.keys())[0]

        final_dict = {"status": "Upload Complete"}

        return jsonify(final_dict), 200

    return jsonify({"status": "Uploading chunk..."}), 200


@app.route("/uploadAir", methods=["POST"])
def uploadAir():

    if "air_data" not in session:
        session["air_data"] = ""

    air_file = request.files.get("file")

    session["air_data"] = air_file.read()

    air_data = generateAirAnimNames(session["air_data"])

    session["air_data"] = air_data

    anim_names = list(air_data.keys())

    return jsonify({"status": "Upload Complete", "anim names": anim_names}), 200


@app.route("/uploadCns", methods=["POST"])
def uploadCns():
    if "cns_data" not in session:
        session["cns_data"] = []

    uploaded_files = request.files.getlist("files")
    if not uploaded_files:
        return jsonify({"error": "No CNS files uploaded"}), 400

    for f in uploaded_files:
        cns_data = f.read().decode("utf-8")
        session["cns_data"].append(cns_data)

    return (
        jsonify({"status": "Upload Complete"}),
        200,
    )


def generateAirAnimNames(air_data):

    air_data = air_data.decode("utf-8").splitlines()
    lines = air_data

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

        i += 1

    actions = {k: v for k, v in actions.items() if v["frames"]}

    return actions


@app.route("/generateAnimPreview", methods=["POST"])
def generateAnimPreview():
    data = request.get_json()

    anim_name = data["animation"]

    sprite_names = session["sprite_data"][list(session["sprite_data"].keys())[0]]

    def get_canvas_bounds(frames, sprite_names):
        min_x, min_y = 0, 0
        max_x, max_y = 0, 0
        for frame in frames:
            img = Image.open(
                io.BytesIO(
                    sprite_names[session["ffe_data"][frame["image"]]["file_name"]]
                )
            ).convert("RGBA")
            ox, oy = frame["offset"]
            min_x = min(min_x, ox)
            min_y = min(min_y, oy)
            max_x = max(max_x, ox + img.width)
            max_y = max(max_y, oy + img.height)
        return min_x, min_y, max_x, max_y

    frames_data = session["air_data"][anim_name]["frames"]

    min_x, min_y, max_x, max_y = get_canvas_bounds(frames_data, sprite_names)
    canvas_width = max_x - min_x
    canvas_height = max_y - min_y

    frames = []
    durations = []

    print(frames_data)

    for frame in frames_data:

        img = Image.open(
            io.BytesIO(sprite_names[session["ffe_data"][frame["image"]]["file_name"]])
        ).convert("RGBA")
        ox, oy = frame["offset"]

        # Create consistent canvas
        canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))

        # Normalize offset: adjust so all frames are relative to min_x/y
        paste_x = ox - min_x
        paste_y = oy - min_y

        alpha_mask = img.getchannel("A")
        canvas.paste(img, (paste_x, paste_y), alpha_mask)

        frames.append(canvas)
        durations.append(frame["duration"] * 10)

    # Save to in-memory GIF
    gif_io = io.BytesIO()
    frames[0].save(
        gif_io,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        disposal=2,
        transparency=0,  # optional if your images have transparency
    )

    webp_io = io.BytesIO()
    frames[0].save(
        webp_io,
        format="WEBP",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        disposal=2,
        transparency=0,
        loop=0,
    )
    webp_io.seek(0)

    gif_io.seek(0)  # Reset pointer to start

    webp_base64 = base64.b64encode(webp_io.read()).decode("utf-8")
    gif_base64 = base64.b64encode(gif_io.read()).decode("utf-8")

    return {"data": gif_base64, "preview": webp_base64}


def add_folder_to_zip(zip_file, folder_tree, current_path=""):
    for name, content in folder_tree.items():
        path_in_zip = f"{current_path}{name}"

        if (
            isinstance(content, dict)
            and "_type" in content
            and content["_type"] == "json"
        ):
            # Convert back parsed JSON to string
            json_text = json.dumps(content["_content"], indent=2)
            zip_file.writestr(path_in_zip, json_text.encode("utf-8"))

        elif isinstance(content, dict):
            # It's a folder
            zip_file.writestr(path_in_zip + "/", "")
            add_folder_to_zip(zip_file, content, path_in_zip + "/")

        elif isinstance(content, (bytes, str)):
            if isinstance(content, str):
                content = content.encode("utf-8")
            zip_file.writestr(path_in_zip, content)

        elif isinstance(content, (list, int, float, bool)):
            # Fallback if somehow plain values get through
            json_text = json.dumps(content, indent=2)
            zip_file.writestr(path_in_zip, json_text.encode("utf-8"))

        else:
            print(f"⚠️ Skipping {path_in_zip}: unsupported type {type(content)}")


def generateAnimation(layers, name):
    animation_guid = str(uuid.uuid4())
    animation_data = {
        "$id": animation_guid,
        "layers": layers,
        "name": name,
        "pluginMetadata": {},
    }

    return animation_guid, animation_data


def generateLayer(keyframes, item_type, hitbox_index=0, hurtbox_index=0):
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


def generateSymbol(
    image_asset=None, item_type="IMAGE", x=0, y=0, scaleX=1, scaleY=1, angle=0
):

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


def generateKeyframe(img_guid, item_type, duration):
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


def addAnimationsToCE(ce_file, project_name):
    print("The big one")
    air_data = session["air_data"]

    for ad in air_data:

        layers = []
        keyframes = []

        hurtbox_count = 0
        hitbox_count = 0

        frames = air_data[ad]["frames"]
        hurtbox_count = max(len(f["hurtboxes"]) for f in frames)
        hitbox_count = max(len(f["hitboxes"]) for f in frames)

        hurtbox_keyframes = [[] for x in range(0, hurtbox_count)]
        hitbox_keyframes = [[] for x in range(0, hitbox_count)]

        def append_collision_keyframe(boxes, box_type, index_list):
            for i in range(len(index_list)):
                if i < len(boxes):
                    hd = boxes[i]
                    box_guid, symbol_data = generateSymbol(
                        item_type="COLLISION_BOX",
                        x=hd[2],
                        y=hd[3],
                        scaleX=-hd[2] + hd[4],
                        scaleY=-hd[3] + hd[5],
                    )
                    ce_file["symbols"].append(symbol_data)
                else:
                    box_guid = None

                keyframe_guid, keyframe_data = generateKeyframe(
                    box_guid, "COLLISION_BOX", f["duration"]
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

                if f["flip"] == "H":
                    scaleX = f["scale"][0] * -1
                    scaleY = f["scale"][1]
                elif f["flip"] == "V":
                    scaleX = f["scale"][0]
                    scaleY = f["scale"][1] * -1
                elif f["flip"] == "HV":
                    scaleX = f["scale"][0] * -1
                    scaleY = f["scale"][1] * -1
                else:
                    scaleX = f["scale"][0]
                    scaleY = f["scale"][1]

                if f["angle"] != 0:
                    angle = 360 - f["angle"]
                    angle_rad = math.radians(angle)
                    temp_x = x
                    temp_y = y
                    x = temp_x * math.cos(angle_rad) - temp_y * math.sin(angle_rad)
                    y = temp_x * math.sin(angle_rad) + temp_y * math.cos(angle_rad)
                else:
                    angle = 0

                img_guid, symbol_data = generateSymbol(
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
                img_guid, symbol_data = generateSymbol(
                    image_asset=None,
                    item_type="IMAGE",
                    x=0,
                    y=0,
                    scaleX=1,
                    scaleY=1,
                    angle=0,
                )

            ce_file["symbols"].append(symbol_data)

            keyframe_guid, keyframe_data = generateKeyframe(
                img_guid, "IMAGE", f["duration"]
            )
            keyframes.append(keyframe_guid)
            ce_file["keyframes"].append(keyframe_data)

            # Append hurtbox and hitbox keyframes
            append_collision_keyframe(f["hurtboxes"], "hurtbox", hurtbox_keyframes)
            append_collision_keyframe(f["hitboxes"], "hitbox", hitbox_keyframes)

        # Generate and append all layers
        def create_layer(kf, itype, index=None):
            layer_guid, layer_data = generateLayer(
                keyframes=kf,
                item_type=itype,
                hurtbox_index=index if itype == "hurtbox" else None,
                hitbox_index=index if itype == "hitbox" else None,
            )
            ce_file["layers"].append(layer_data)
            layers.append(layer_guid)

        create_layer(keyframes, "image")

        for i, kfs in enumerate(hurtbox_keyframes):
            create_layer(kfs, "hurtbox", i)

        for i, kfs in enumerate(hitbox_keyframes):
            create_layer(kfs, "hitbox", i)

        animation_guid, animation_data = generateAnimation(layers, ad)

        ## Record layer to ce_file
        ce_file["animations"].append(animation_data)

    ce_file["id"] = project_name

    return ce_file


## Update scripts with a new project name
def updateScripts(scripts, project_name):
    for s in scripts:
        if ".meta" in s:
            file_name = s.split(".")[0]
            scripts[s]["_content"]["id"] = project_name + file_name

        elif s == "CharacterStats.hx":
            print(scripts[s])

            updated = re.sub(
                b'(?<=self\\.getResource\\(\\)\\.getContent\\(")(.*?)(?=")',
                project_name.encode("utf-8"),
                scripts[s],
            )
            scripts[s] = updated

    return scripts


## Update the manifest with new project_name
def updateManifest(manifest, project_name):
    manifest["resourceId"] = project_name

    for c in manifest["content"][0]:
        if c == "id":
            manifest["content"][0][c] = project_name
        elif c == "name":
            manifest["content"][0][c] = project_name
        elif c == "description":
            manifest["content"][0][c] = (
                project_name
                + "was imported by the Fraytools Animation Importer by Zardy Z"
            )
        elif c == "objectStatsId":
            manifest["content"][0][c] = project_name + "CharacterStats"
        elif c == "animationStatsId":
            manifest["content"][0][c] = project_name + "AnimationStats"
        elif c == "hitboxStatsId":
            manifest["content"][0][c] = project_name + "HitboxStats"
        elif c == "scriptId":
            manifest["content"][0][c] = project_name + "Script"
        elif c == "costumesId":
            manifest["content"][0][c] = project_name + "Costumes"
        elif c == "aiId":
            manifest["content"][0][c] = project_name + "Ai"

    ai_code = manifest["content"][1]
    ai_code["id"] = project_name + "Ai"
    ai_code["scriptId"] = project_name + "Ai"

    manifest["content"][1] = ai_code

    return manifest


## Update the costume.palettes file with the new project_name for id
def updateCostumes(costumes, project_name):
    costumes["id"] = project_name + "Costumes"
    return costumes


def parse_cns_file(lines):
    state_to_anim = {}
    current_state = None

    for line in lines:
        line = line.strip()

        match_state = re.match(r"\[Statedef (\d+)\]", line)
        if match_state:
            current_state = int(match_state.group(1))

        match_anim = re.match(r"anim\s*=\s*(\d+)", line, re.IGNORECASE)
        if match_anim and current_state is not None:
            state_to_anim[current_state] = int(match_anim.group(1))
    return state_to_anim


@app.route("/importCharacter", methods=["POST"])
def importCharacter():

    cns_files = session["cns_data"]

    state_anim_map = {}

    for cns_text in cns_files:
        state_anim_map.update(parse_cns_file(cns_text.splitlines()))

    print(state_anim_map)

    data = request.get_json()
    app_root = current_app.root_path
    project_name = data["projectName"]

    base_folder = "\\fraymakers-templates\\" + data["template"]
    base_folder = app_root + base_folder

    folder_tree = createFolderStructureFromDisk(base_folder)

    for f in list(folder_tree.keys()):
        print(f)
        if ".fraytools" in f:
            folder_tree[project_name + ".fraytools"] = folder_tree.pop(f)

    ## Add in sprites from sprite folder to project files
    ## Need to remove any file that is not .meta or .png
    folder_tree["library"]["sprites"][session["sprite_name"]] = session["sprite_data"][
        session["sprite_name"]
    ]

    project_name = data["projectName"]

    ce_file = folder_tree["library"]["entities"]["character.entity"]["_content"]
    ce_file = addAnimationsToCE(ce_file, project_name)

    ## Update script names with new project_name
    scripts = folder_tree["library"]["scripts"]["Character"]
    scripts = updateScripts(scripts, project_name)

    manifest = folder_tree["library"]["manifest.json"]["_content"]
    manifest = updateManifest(manifest, project_name)

    costumes = folder_tree["library"]["costumes.palettes"]["_content"]
    costumes = updateCostumes(costumes, project_name)

    folder_tree = {project_name: folder_tree}

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        add_folder_to_zip(zip_file, folder_tree)

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=project_name + ".zip",
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
