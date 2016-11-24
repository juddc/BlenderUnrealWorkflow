"""
Unreal engine 4 modelling workflow toolset

Author: Judd Cohen
License: MIT
"""
import bpy
import math
from bpy.props import BoolProperty, StringProperty, FloatProperty

bl_info = {
    "name": "Unreal Workflow",
    "author": "Judd Cohen",
    "version": (0, 9, 0),
    "blender": (2, 7, 8),
    "location": "View3D > Tools > Unreal Workflow",
    "description": "Toolset for working with Unreal Engine 4",
    "warning": "",
    "wiki_url": "http://www.soundgm.com/",
    "category": "Unreal Engine 4"}



class UnrealExportProps(bpy.types.PropertyGroup):
    """
    Property group for all settings required for exporting meshes
    """
    bl_idname = "unrealworkflow.group"
    bl_label = "Unreal Export Props"

    use_object_origin = BoolProperty(
        name="Use Object Origin",
        default=True,
        description="Exports each object with its own origin as the origin of the file.",
    )

    selected_only = BoolProperty(
        name="Selected Only",
        default=True,
        description="Only export selected meshes (if false, will export all meshes)",
    )

    include_collision = BoolProperty(
        name="Include Collision",
        default=True,
        description="Include collision meshes (with names beginning with 'UCX_') with their respective meshes.",
    )

    auto_uvs = BoolProperty(
        name="Automatic UVs",
        default=False,
        description="Ensures that all meshes have a UV cube projection modifier associated with them",
    )

    scale = FloatProperty(
        name="Scale",
        default=1.0,
        description="FBX export scale",
    )

    export_path = StringProperty(
        name="Export Path",
        default="//",
        description="The directory path to export the FBX files to",
    )



def deg2rad(angle):
    return math.pi * angle / 180.0



def move_to_workflow_layer(obj):
    """
    Helper function to move any object to the very last layer
    """
    layers = [False] * 20
    layers[-1] = True
    obj.layers = layers



def parse_ucx(name):
    """
    Helper function that takes an object name and returns a 2-tuple consisting of
    the original object name (without 'UCX_' prefix) and UCX index suffix as an int.

    https://docs.unrealengine.com/latest/INT/Engine/Content/FBX/StaticMeshes/index.html#collision

    Will return (None, None) if the input name is not a UCX_ at all.

    Will return an index of -1 if the input is a UCX, but no index could be parsed.
    """
    if not name.startswith("UCX_"):
        return (None, None)
    else:
        # strip UCX_ prefix
        name = name[4:]

    # index starting value
    idx = -1

    # check if this has Blender's duplicated object naming scheme
    if len(name) > 4:
        if name[-1].isdigit() and name[-2].isdigit() and name[-3].isdigit() and name[-4] == ".":
            # add to the index whatever value is in the last 3 digits
            idx += int(name[-3:])
            # strip the numbers and dot from the name
            name = name[:-4]

    # extract all characters from the end that are numerica
    last_digits = []
    for i in range(1, len(name)):
        if name[-i].isdigit():
            last_digits.insert(0, name[-i])
        else:
            break

    # strip the digits off the end of the name
    name = name[:-len(last_digits)]

    # if there was a dot or underscore seperating the digit, strip that too
    if name.endswith(".") or name.endswith("_"):
        name = name[:-1]

    # convert last digits (an array of digit characters) into an int
    try:
        idx += int("".join(last_digits))
    except ValueError:
        # failed to get an index, but this is still a UCX
        return (name, idx)

    return (name, idx)


def format_ucx(name, idx):
    """
    Formats a name and index as a collider
    """
    # one digit of zero padding
    idxstr = str(idx).zfill(2)
    return "UCX_%s_%s" % (name, idxstr)



class UVCubeProjectModifier(bpy.types.Operator):
    """
    Sets up a UV Cube Projection modifier
    """
    bl_idname = "unrealworkflow.uvcubeproject"
    bl_label = "Add UV Cube Projection"
    bl_options = {'REGISTER', 'UNDO'}


    def create_ortho_camera(self, name, euler):
        """
        Helper function to create an ortho camera for use by the auto-UV system
        """
        cam = bpy.data.cameras.new(name)
        cam_obj = bpy.data.objects.new(name, cam)
        bpy.context.scene.objects.link(cam_obj)
        cam_obj.data.type = 'ORTHO'
        cam_obj.data.ortho_scale = 1.0
        cam_obj.location = (0.0, 0.0, 0.0)
        cam_obj.rotation_euler = [ deg2rad(euler[0]), deg2rad(euler[1]), deg2rad(euler[2]) ]
        move_to_workflow_layer(cam_obj)
        return cam_obj


    def get_or_create_camera(self, context, name, rot):
        """
        Retrieves the requested camera, creating it if needed
        """
        found_camera = None

        for obj_name, obj in context.scene.objects.items():
            if obj_name.startswith(name):
                found_camera = obj_name
                break

        if found_camera is not None:
            return context.scene.objects[found_camera]
        else:
            return self.create_ortho_camera(name, rot)


    def get_cameras(self, context):
        """
        Returns a list of 6 cameras, each pointing in a different direction
        """
        cameras = []

        cameras.append(self.get_or_create_camera(context, "Camera_X+", (90.0, 0.0, 270.0)))
        cameras.append(self.get_or_create_camera(context, "Camera_X-", (90.0, 0.0, 90.0)))

        cameras.append(self.get_or_create_camera(context, "Camera_Y+", (90.0, 0.0, 0.0)))
        cameras.append(self.get_or_create_camera(context, "Camera_Y-", (90.0, 0.0, 180.0)))

        cameras.append(self.get_or_create_camera(context, "Camera_Z+", (180.0, 0.0, 0.0)))
        cameras.append(self.get_or_create_camera(context, "Camera_Z-", (0.0, 0.0, 0.0)))

        return cameras


    def execute(self, context):
        """
        Add a UV_PROJECT modifier with a pre-set camera setup
        """
        for ob in context.selected_objects:
            if ob.type == "MESH":
                # make sure the mesh has at least one UV map for the modifier to work on
                if len(ob.data.uv_textures) == 0:
                    ob.data.uv_textures.new()

                # create and configure the modifier
                ob.modifiers.new(type="UV_PROJECT", name="UVCubeProjection")
                mod = ob.modifiers["UVCubeProjection"]
                cameras = self.get_cameras(context)
                mod.projector_count = len(cameras)
                for i in range(len(cameras)):
                    mod.projectors[i].object = cameras[i]
                mod.scale_x = 1.0
                mod.scale_y = 1.0

        return {'FINISHED'}



class SetCollisionMeshDrawType(bpy.types.Operator):
    """
    Set the draw type of all UCX_ collision meshes at once.
    """
    bl_idname = "unrealworkflow.setcollisionmesh_drawtype"
    bl_label = "Set Collision Mesh Draw Type"
    bl_options = {'REGISTER', 'UNDO'}

    # operator arguments
    draw_type = StringProperty(default="WIRE")


    def draw(self, context):
        col = self.layout.column()
        col.prop(self.draw_type, "Draw type")


    def execute(self, context):
        """
        Set draw type for all colliders at once
        """
        for obj in context.scene.objects:
            name, index = parse_ucx(obj.name)
            if name is not None:
                obj.draw_type = self.draw_type
        return {'FINISHED'}



class CreateCollision(bpy.types.Operator):
    """
    Makes a copy of the selected mesh, marks the copy as a collider, and sets the
    draw type to Wireframe.
    """
    bl_idname = "unrealworkflow.createcollision"
    bl_label = "Create Collision"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        """
        Copy the existing mesh, rename it to a collider, and set a wireframe draw type
        """
        base = context.scene.objects.active

        if base.type != "MESH":
            self.report({'ERROR'}, "Can only create collision from a mesh")
            return {'CANCELLED'}

        if len(context.selected_objects) > 1:
            self.report({'ERROR'}, "Need just one object selected (got %i)" %
                len(context.selected_objects))
            return {'CANCELLED'}

        if 'FINISHED' in bpy.ops.object.duplicate():
            # duplicated object is the new active one
            ucx = context.scene.objects.active
            ucx.name = format_ucx(base.name, 1)
            ucx.draw_type = "WIRE"

        return {'FINISHED'}



class RenameCollisionMeshes(bpy.types.Operator):
    """
    Using the active selected mesh as the base object, takes all other selected
    meshes as well as any other meshes currently matching the base object with a
    UCX_ prefix and renames them to have consistent naming and numbering.
    """
    bl_idname = "unrealworkflow.renamecollisionmeshes"
    bl_label = "Rename Collision Meshes"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        """
        Assume the active mesh is the base, and rename all other selected objects
        as well as existing UCX_ prefixed colliders to consistently follow the UCX
        naming convention
        """
        base = context.scene.objects.active

        # find any colliders that already have a UCX_ prefix
        existing = []
        for obj in context.scene.objects:
            if obj.type == "MESH":
                ucx_name, ucx_index = parse_ucx(obj.name)
                if ucx_name == base.name:
                    existing.append( (obj, ucx_index) )

        # sort by existing index so the order can be maintained
        existing.sort(key=lambda x: x[1])

        all_ucx = []

        # add existing collision objects
        for obj, idx in existing:
            all_ucx.append(obj)

        # add any additional selected objects
        for obj in context.selected_objects:
            if obj != base and obj not in all_ucx:
                all_ucx.append(obj)

        # rename all the meshes in order
        for i in range(len(all_ucx)):
            all_ucx[i].name = format_ucx(base.name, i + 1)

        return {'FINISHED'}



class SelectCollisionMeshes(bpy.types.Operator):
    """
    Select all meshes that are marked as colliders (UCX_ prefix) for the selected mesh
    """
    bl_idname = "unrealworkflow.selectcollisionmeshes"
    bl_label = "Select Collision Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """
        Select all colliders with the same base name
        """
        base = context.scene.objects.active

        # deselect all except the base
        for obj in context.scene.objects:
            if obj != base:
                obj.select = False

        count = 0

        # select any mesh that matches the UCX name
        for obj in context.scene.objects:
            if obj.type == "MESH":
                ucx_name, ucx_index = parse_ucx(obj.name)
                if ucx_name == base.name:
                    obj.select = True
                    count += 1

        self.report({'INFO'}, "Selected %i meshes" % count)

        return {'FINISHED'}



class ResetColliderOrigin(bpy.types.Operator):
    """
    Sets the origin of all selected colliders to the origin of the mesh each represents.
    """
    bl_idname = "unrealworkflow.resetcolliderorigin"
    bl_label = "Reset Collider Origin"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        """
        Fix collider origin
        """
        # save the cursor location so we can restore it when we're done
        cursor_loc = (
            context.scene.cursor_location[0],
            context.scene.cursor_location[1],
            context.scene.cursor_location[2])

        colliders = []

        for obj in context.selected_objects:
            name, index = parse_ucx(obj.name)
            if name is None:
                self.report({"ERROR"}, "Selected object '%s' is not a collider" % obj.name)
                return {"CANCELLED"}
            elif name in context.scene.objects:
                colliders.append( (obj, context.scene.objects[name]) )
            else:
                self.report({"ERROR"}, "No base object found: %s" % name)
                return {"CANCELLED"}

        for collider, base in colliders:
            bpy.ops.object.select_all(action='DESELECT')
            base.select = True
            bpy.ops.view3d.snap_cursor_to_selected()
            base.select = False
            collider.select = True
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR")

        # restore cursor to where it was before using this tool
        context.scene.cursor_location = cursor_loc

        return {'FINISHED'}



class UnrealExporter(bpy.types.Operator):
    """
    Export FBX files for use with Unreal Engine 4
    """
    bl_idname = "unrealworkflow.exporter"
    bl_label = "Export to Unreal"
    bl_options = {'REGISTER', 'UNDO'}

    export_scene_name = "Unreal Export Scene"


    def _in_export_scene(self, context):
        """
        Is the exporter scene the active one?
        """
        return context.scene.name == self.export_scene_name


    def _create_scene(self, context):
        """
        Creates a scene that will represent the exported FBX
        """
        bpy.ops.scene.new()
        context.scene.name = self.export_scene_name


    def _clear_scene(self, context):
        """
        Removes all objects in the exporter scene
        """
        if context.scene.name == self.export_scene_name:
            bpy.ops.object.select_all(action='DESELECT')
            for obj in context.scene.objects:
                obj.select = True
                bpy.ops.object.delete()


    def _remove_scene(self, context):
        """
        Removes the exporter scene
        """
        self._clear_scene(context)
        if context.scene.name == self.export_scene_name:
            #print("delete!")
            bpy.ops.scene.delete()


    def _copy_object_to_current_scene(self, context, obj, newname):
        """
        Copy an object and all of its modifiers to a new object in a different scene.
        (Shares data with the object in the original scene)
        """
        newobj = bpy.data.objects.new(newname, obj.data)
        context.scene.objects.link(newobj)

        # make sure the name is set (blender can change these if there is a conflict)
        if newobj.name != newname:
            newobj.name = newname

        # copy over all modifiers
        for src in obj.modifiers:
            dest = newobj.modifiers.get(src.name, None)
            if not dest:
                dest = newobj.modifiers.new(src.name, src.type)
            for prop in [ p.identifier for p in src.bl_rna.properties if not p.is_readonly ]:
                setattr(dest, prop, getattr(src, prop))

                # UV_PROJECT modifier needs some special-case handling for the camera references
                if dest.type == "UV_PROJECT":
                    dest.projector_count = src.projector_count
                    for i in range(dest.projector_count):
                        dest.projectors[i].object = src.projectors[i].object

        return newobj


    def export(self, context, props, object_types, meshobj, collision):
        """
        Exports the exporter scene to its own FBX file
        """
        # MUST be in the export scene to export
        if not self._in_export_scene(context):
            raise Exception("Invalid scene setup for exporting")

        filepath = "{path}/{name}.fbx".format(
            path=bpy.path.abspath(props.export_path),
            name=meshobj.name)

        # add an _EXPORT suffix to avoid a name conflict with the base scene
        meshname = "%s_EXPORT" % meshobj.name

        # make a reference to the mesh in the new scene
        exobj = self._copy_object_to_current_scene(context, meshobj, meshname)
        if not props.use_object_origin:
            exobj.location = meshobj.location

        for obj in collision:
            # add an _EXPORT suffix to avoid a name conflict with the base scene
            ucxname, idx = parse_ucx(obj.name)
            name = format_ucx("%s_EXPORT" % ucxname, idx)

            # make a reference to the collider in the new scene
            self._copy_object_to_current_scene(context, obj, name)
            if not props.use_object_origin:
                colobj.location = obj.location

        # export the exporter scene to an FBX file
        try:
            bpy.ops.export_scene.fbx(
                check_existing=True,
                filepath=filepath,
                filter_glob="*.fbx",
                version="BIN7400", # or ASCII6100
                use_selection=False,
                global_scale=props.scale,
                axis_forward="-Z",
                axis_up="Y",
                bake_space_transform=False,
                object_types=object_types,
                use_mesh_modifiers=True,
                batch_mode="OFF",
                path_mode="AUTO",
                embed_textures=False,
            )
        except Exception as e:
            self.report({'ERROR'}, "Failed to export")
            raise


    def execute(self, context):
        """
        Export each mesh object as its own FBX file
        """
        if not hasattr(context.scene, "unreal_export_props"):
            self.report({'ERROR'}, "Failed to retrieve export settings")
            return {'CANCELLED'}

        # export settings
        props = context.scene.unreal_export_props

        # valid object types (all others will be ignored)
        object_types = {'MESH'}

        # all meshes that will be exported
        exported = []

        # gather all the meshes that will be exported
        if props.selected_only:
            for obj in context.selected_objects:
                if obj.type in object_types and not obj.name.startswith("UCX_"):
                    exported.append({ 'mesh': obj, 'col': [] })
        else:
            for obj in context.scene.objects:
                if obj.type in object_types and not obj.name.startswith("UCX_"):
                    exported.append({ 'mesh': obj, 'col': [] })

        # populate collision lists
        if props.include_collision:
            for data in exported:
                ucx_meshes = []

                # find UCX_ meshes for collision
                for ucx in context.scene.objects:
                    if ucx.type == "MESH":
                        orig_name, ucx_index = parse_ucx(ucx.name)
                        if orig_name == data['mesh'].name:
                            ucx_meshes.append( (ucx, ucx_index) )

                # sort by ucx index
                ucx_meshes.sort(key=lambda a: a[1])

                # strip index data and associate the colliders with their parent mesh
                data['col'] = [ obj for obj, _ in ucx_meshes ]

        # we need a scene to fix transforms to be object-local instead of scene local
        self._create_scene(context)

        # export the mesh and its colliders to its own FBX file
        for data in exported:
            # export but make sure to clean up the temp scene in case something went wrong
            try:
                self._clear_scene(context)
                self.export(context, props, object_types, data['mesh'], data['col'])

            except Exception as e:
                self.report({'ERROR'}, "Error exporting: %s" % e)
                self._remove_scene(context)
                return {'CANCELLED'}

        self._remove_scene(context)
        return {'FINISHED'}



class MeshToolsPanel(bpy.types.Panel):
    """
    Tools panel for exposing all the non-exporting functionality
    """
    bl_category = "Unreal Engine 4"
    bl_label = "Mesh Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"


    def draw(self, context):
        row = self.layout.row()
        col = row.column(align=True)

        col.operator("unrealworkflow.uvcubeproject", icon="MODIFIER")
        col.separator()

        col.operator("unrealworkflow.createcollision", icon="OUTLINER_DATA_MESH")
        col.separator()

        col.operator("unrealworkflow.resetcolliderorigin", icon="SNAP_VERTEX")
        col.separator()

        col.operator("unrealworkflow.selectcollisionmeshes", icon="UV_SYNC_SELECT")
        col.separator()

        col.operator("unrealworkflow.renamecollisionmeshes", icon="OUTLINER_DATA_FONT")
        col.separator()

        col.label("Set collision mesh draw type:")
        dt_box = col.box()
        dt_row = dt_box.row()
        dt_wire = dt_row.operator("unrealworkflow.setcollisionmesh_drawtype", text="Wire", icon="WIRE")
        dt_wire.draw_type = "WIRE"
        #dt_solid = dt_row.operator("unrealworkflow.setcollisionmesh_drawtype", text="Solid", icon="SOLID")
        #dt_solid.draw_type = "SOLID"
        dt_solid = dt_row.operator("unrealworkflow.setcollisionmesh_drawtype", text="Textured", icon="TEXTURE_SHADED")
        dt_solid.draw_type = "TEXTURED"
        col.separator()



class ExportSettingsPanel(bpy.types.Panel):
    """
    Panel for all the exporting functionality
    """
    bl_category = "Unreal Engine 4"
    bl_label = "Export Settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "TOOLS"


    def _export_prop(self, parent, props, name, label=None):
        """
        Helper for exporter setting layout
        """
        row = parent.row()
        if label is None:
            row.prop(props, name)
        else:
            row.prop(props, name, text=label)


    def draw(self, context):
        row = self.layout.row()
        col = row.column()

        if hasattr(context.scene, "unreal_export_props"):
            box = col.box()
            props = context.scene.unreal_export_props
            self._export_prop(box, props, "use_object_origin")
            self._export_prop(box, props, "selected_only")
            self._export_prop(box, props, "include_collision")
            #self._export_prop(box, props, "auto_uvs")
            self._export_prop(box, props, "export_path")
            self._export_prop(box, props, "scale")
            col.separator()

        col.operator("unrealworkflow.exporter", icon="EXPORT")



# all classes to register and unregister
Classes = [
    UnrealExportProps,
    MeshToolsPanel,
    ExportSettingsPanel,
    UVCubeProjectModifier,
    SetCollisionMeshDrawType,
    CreateCollision,
    ResetColliderOrigin,
    SelectCollisionMeshes,
    RenameCollisionMeshes,
    UnrealExporter,
]



# all properties to register and unregister
Properties = {
    "unreal_export_props": bpy.props.PointerProperty(type=UnrealExportProps),
}



def register():
    for cls in Classes:
        bpy.utils.register_class(cls)
    for name, prop in Properties.items():
        setattr(bpy.types.Scene, name, prop)



def unregister():
    for cls in Classes:
        bpy.utils.unregister_class(cls)
    for name, prop in Properties.items():
        delattr(bpy.types.Scene, name)



if __name__ in "__main__":
    register()
