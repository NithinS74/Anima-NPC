"""Run only with portable Blender --background --python ... -- manifest.json.

Independent conversion script using installed PyNifly and Blender APIs. No
game/tool implementation is copied here. Output stays under private lab assets.
"""

import json
import sys
from pathlib import Path


def main():
    import bpy
    manifest = json.loads(Path(sys.argv[sys.argv.index("--") + 1]).read_text(encoding="utf-8"))
    source = Path(manifest["source"])
    sys.path.insert(0, manifest["addon_directory"])
    bpy.ops.preferences.addon_enable(module="io_scene_nifly")
    bpy.context.preferences.addons["io_scene_nifly"].preferences.sky_texture_path_1 = str(source)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for name in manifest["meshes"]:
        bpy.ops.object.select_all(action="DESELECT")
        bpy.context.view_layer.objects.active = None
        bpy.ops.import_scene.pynifly(filepath=str(source / name), import_collisions=False,
                                   import_animations=False, import_tris=False, import_shapekeys=False)
    # Simplify game shader groups to a portable glTF base-color material. Keep
    # actual game diffuse/face-tint images; no web texture/network dependencies.
    for material in list(bpy.data.materials):
        if not material.node_tree:
            continue
        nodes = material.node_tree.nodes
        diffuse = next((n.image for n in nodes if n.type == "TEX_IMAGE" and "diffuse" in n.name.lower() and n.image), None)
        alpha = any("alphaproperty" in n.name.lower() for n in nodes)
        if "head" in material.name.lower():
            head = manifest["meshes"][0].split("/")[-1].removesuffix(".nif")
            tint = source / f"textures/actors/character/facegendata/facetint/skyrim.esm/{head}.dds"
            if tint.is_file():
                diffuse = bpy.data.images.load(str(tint), check_existing=True)
        nodes.clear()
        output = nodes.new("ShaderNodeOutputMaterial")
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        shader.inputs["Roughness"].default_value = 0.85
        material.node_tree.links.new(shader.outputs["BSDF"], output.inputs["Surface"])
        if diffuse:
            if max(diffuse.size) > 1024:
                ratio = 1024 / max(diffuse.size)
                diffuse.scale(max(1, int(diffuse.size[0] * ratio)), max(1, int(diffuse.size[1] * ratio)))
            # DDS cannot be embedded directly in standard glTF. Save an actual
            # PNG conversion before packing so alpha/face tint survive export.
            converted = source / "converted_textures" / (diffuse.name + ".png")
            converted.parent.mkdir(exist_ok=True)
            diffuse.filepath_raw = str(converted); diffuse.file_format = "PNG"; diffuse.save(); diffuse.pack()
            image = nodes.new("ShaderNodeTexImage"); image.image = diffuse
            material.node_tree.links.new(image.outputs["Color"], shader.inputs["Base Color"])
            if alpha:
                material.surface_render_method = "DITHERED"
                material.node_tree.links.new(image.outputs["Alpha"], shader.inputs["Alpha"])
        else:
            shader.inputs["Base Color"].default_value = (0.3, 0.27, 0.22, 1)
    # Freeze evaluated geometry into one static assembled character. This is
    # presentation, not an animation/retargeting or game-state implementation.
    depsgraph = bpy.context.evaluated_depsgraph_get()
    originals = list(bpy.data.objects)
    baked = []
    for obj in originals:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        mesh.transform(obj.matrix_world)
        for material in obj.data.materials:
            if material.name not in mesh.materials:
                mesh.materials.append(material)
        fresh = bpy.data.objects.new("Skyrim_" + obj.name, mesh)
        bpy.context.collection.objects.link(fresh); baked.append(fresh)
    for obj in originals:
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in baked:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = baked[0]
    output = Path(manifest["output"]); output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(output), export_format="GLB", use_selection=True,
                              export_animations=False, export_skins=False, export_morph=False,
                              export_image_format="AUTO", export_yup=True)
    backdrop = Path(manifest.get("background_source", ""))
    if backdrop.is_file():
        image = bpy.data.images.load(str(backdrop), check_existing=True)
        if max(image.size) > 1024:
            ratio = 1024 / max(image.size)
            image.scale(max(1,int(image.size[0]*ratio)), max(1,int(image.size[1]*ratio)))
        target = Path(manifest["background_output"]); target.parent.mkdir(parents=True, exist_ok=True)
        image.filepath_raw = str(target); image.file_format = "PNG"; image.save()
    print("LAB_EXPORTED", str(output), output.stat().st_size, flush=True)


if __name__ == "__main__":
    main()
