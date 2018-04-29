import bpy, bmesh
from bpy.props import *
from . import common
from mathutils import Vector, Matrix

def bmesh_vert_active(bm):
    if bm.select_history:
        elem = bm.select_history[-1]
        if isinstance(elem, bmesh.types.BMVert):
            return elem
    return None

def bmesh_edge_active(bm):
    if bm.select_history:
        elem = bm.select_history[-1]
        if isinstance(elem, bmesh.types.BMEdge):
            return elem
    return None

class ObjectState:
    def __init__(self, obj):
        self.obj = obj
        self.active_shape_key_index = obj.active_shape_key_index

    def revert(self):
        self.obj.active_shape_key_index = self.active_shape_key_index

class ForceMirrorAdvance(bpy.types.Operator):
    bl_idname = "mesh.force_mirror_advance"
    bl_label = "Force Mirror to Basemesh (Advance)"
    bl_description = "Force mirror to basemesh and only works on basemesh"
    bl_options = {'REGISTER', 'UNDO'}

    def remember(self, context):
        # Remember Scene
        self.scene = context.scene
        self.tool_settings = context.tool_settings
        self.selects = [o.name for o in self.scene.objects if o.select]

        # Remember object stuff
        self.obj = context.object
        self.obj_mode = self.obj.mode
        self.active_shape_key_index = self.obj.active_shape_key_index

    def recover(self):
        bpy.ops.object.mode_set(mode=self.obj_mode)

    # Assumed happen in object mode
    def delete_half(self, obj, direction):

        self.scene.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.symmetrize(direction = direction)
        bpy.ops.mesh.select_all(action='DESELECT')

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        #bpy.ops.mesh.select_mode(type="FACE")
        self.tool_settings.mesh_select_mode = (False, False, True)

        if direction == 'POSITIVE_X':
            for f in bm.faces:
                if f.calc_center_median().x < 0.0:
                    f.select = True
        elif direction == 'NEGATIVE_X':
            for f in bm.faces:
                if f.calc_center_median().x > 0.0:
                    f.select = True

        bpy.ops.mesh.delete(type='FACE')
        bpy.ops.object.mode_set(mode='OBJECT')

    # Assumed happen in object mode
    def separate_half(self, obj, direction):

        # Populate original objects on scene
        obj_names = [o.name for o in self.scene.objects]

        self.scene.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')

        bm = bmesh.from_edit_mesh(obj.data)
        bm.faces.ensure_lookup_table()

        if direction == 'POSITIVE_X':
            for f in bm.faces:
                if f.calc_center_median().x < 0.0:
                    f.select = True
        elif direction == 'NEGATIVE_X':
            for f in bm.faces:
                if f.calc_center_median().x > 0.0:
                    f.select = True

        bpy.ops.mesh.separate(type='SELECTED')

        bpy.ops.object.mode_set(mode='OBJECT')

        sep_obj = [o for o in self.scene.objects if o.name not in obj_names][0]

        return sep_obj

    def check_similar(self, obj1, obj2):
        polys1 = [p for p in obj1.data.polygons]
        polys2 = [p for p in obj2.data.polygons]
        
        result = {}

        for p1 in polys1:
            p2 = None
            for p in polys2:
                #if (p1.center - p.center).length < 0.00001:
                if (p1.center - p.center).length < 0.0001:
                    p2 = p
                    break
            if p2:
                result[p1.index] = p2.index
        
        return result

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):

        self.remember(context)

        obj = context.object
        scene = context.scene

        # Reset transfrom
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        #obj.matrix_world = Matrix()

        # UV from island for unmarked meshes
        scene.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.seams_from_islands()
        bpy.ops.object.mode_set(mode='OBJECT')

        # Duplicate two copy for original left and right
        obj.select = True
        bpy.ops.object.duplicate()
        ori_half = context.object
        ori_half.name = '_ORIGINAL_HALF'

        # Delete half of the duplicate objects
        self.delete_half(ori_half, 'NEGATIVE_X')

        # Mirror main object
        scene.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.symmetrize(direction = 'POSITIVE_X')
        
        bpy.ops.object.mode_set(mode='OBJECT')

        # Separate half
        mirror_half = self.separate_half(obj, 'POSITIVE_X')
        mirror_half.name = '_MIRRORED_HALF'

        # Check pair face id to original half
        pair_ids = self.check_similar(mirror_half, ori_half)

        # Separate again for faces with pairs
        obj_names = [o.name for o in self.scene.objects]
        scene.objects.active = mirror_half
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        self.tool_settings.mesh_select_mode = (False, False, True)

        bm = bmesh.from_edit_mesh(mirror_half.data)
        bm.faces.ensure_lookup_table()
        for i, j in pair_ids.items():
            bm.faces[i].select = True

        bpy.ops.mesh.separate(type='SELECTED')
        bpy.ops.object.mode_set(mode='OBJECT')

        mirror_half_with_pairs = [o for o in self.scene.objects if o.name not in obj_names][0]
        mirror_half_with_pairs.name = '_MIRRORED_HALF_WITH_PAIRS'

        # Sort faces for transfer consistency
        scene.objects.active = mirror_half_with_pairs
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.sort_elements(type='CURSOR_DISTANCE', elements={'VERT', 'EDGE', 'FACE'})
        bpy.ops.object.mode_set(mode='OBJECT')

        # Duplicate original half just in case
        bpy.ops.object.select_all(action='DESELECT')
        scene.objects.active = ori_half
        ori_half.select = True
        bpy.ops.object.duplicate()
        ori_half_with_pairs = context.object
        ori_half_with_pairs.name = '_ORIGINAL_HALF_WITH_PAIRS'

        # Delete non paired half on original half duplicate
        scene.objects.active = ori_half_with_pairs
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        self.tool_settings.mesh_select_mode = (False, False, True)

        bm = bmesh.from_edit_mesh(ori_half_with_pairs.data)
        bm.faces.ensure_lookup_table()
        for i, j in pair_ids.items():
            bm.faces[j].select = False

        bpy.ops.mesh.delete(type='FACE')

        # Sort faces for transfer consistency
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.sort_elements(type='CURSOR_DISTANCE', elements={'VERT', 'EDGE', 'FACE'})

        bpy.ops.object.mode_set(mode='OBJECT')

        # Transfer uv from originals
        bpy.ops.object.select_all(action='DESELECT')
        ori_half_with_pairs.select = True
        mirror_half_with_pairs.select = True
        scene.objects.active = ori_half_with_pairs

        bpy.ops.object.join_uvs()
        #bpy.ops.object.data_transfer(data_type='SEAM')
        #bpy.ops.object.data_transfer(data_type='UV')
        

        # Join all
        bpy.ops.object.select_all(action='DESELECT')
        mirror_half.select = True
        mirror_half_with_pairs.select = True
        obj.select = True
        scene.objects.active = obj
        bpy.ops.object.join()

        # Remove doubles
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.object.mode_set(mode='OBJECT')

        # Delete leftovers
        bpy.ops.object.select_all(action='DESELECT')
        ori_half.select = True
        ori_half_with_pairs.select = True
        bpy.ops.object.delete()

        self.recover()

        return {'FINISHED'}

class ForceMirror(bpy.types.Operator):
    bl_idname = "mesh.force_mirror"
    bl_label = "Force Mirror to Basemesh"
    bl_description = "Force mirror to basemesh and only works on basemesh"
    bl_options = {'REGISTER', 'UNDO'}

    mode = EnumProperty(
            name = "Mirror Mode",
            items = (('X_PLUS_MIN', "X+ to X-", ""),
                     ('X_MIN_PLUS',  "X- to X+", ""),
                     ('Y_PLUS_MIN',  "Y+ to Y-", ""),
                     ('Y_MIN_PLUS',  "Y- to Y+", ""),
                     ('Z_PLUS_MIN',  "Z+ to Z-", ""),
                     ('Z_MIN_PLUS',  "Z- to Z+", "")),
            default = 'X_PLUS_MIN')

    def check_similar(self, obj1, obj2):
        polys1 = [p for p in obj1.data.polygons]
        polys2 = [p for p in obj2.data.polygons]
        
        poly1_result = []
        poly2_result = []

        for p1 in polys1:
            p2 = None
            for p in polys2:
                #if (p1.center - p.center).length < 0.00001:
                if (p1.center - p.center).length < 0.0001:
                    p2 = p
                    break
            if p2:
                poly1_result.append(p1.index)
                poly2_result.append(p2.index)
                polys2.remove(p2)
        
        return { obj1.name : poly1_result,
                 obj2.name : poly2_result }

    def flip_vertex_group(self, obj):
        vg_founds = []
        for vg in obj.vertex_groups:

            if vg in vg_founds: 
                continue

            vg_name = vg.name
            mir_name = common.get_mirror_name(vg.name)
            #print(vg.name, mir_name)

            mir_vg = obj.vertex_groups.get(mir_name)
            if mir_vg:

                mir_vg.name = '_____TEMP____'
                vg.name = mir_name
                mir_vg.name = vg_name

                vg_founds.append(vg)
                vg_founds.append(mir_vg)

    def remember(self, context):
        ### Remember Scene
        self.scene = context.scene

        # Save active object
        self.active_object = self.scene.objects.active
        if self.active_object:
            self.active_object_mode = self.active_object.mode

        # Save every object attributes
        self.selects = {}
        self.hides = {}
        #self.modes = {}
        for obj in self.scene.objects:
            self.selects[obj.name] = obj.select
            self.hides[obj.name] = obj.hide
            #self.modes[obj.name] = obj.mode

        self.layers = []
        for l in self.scene.layers:
            self.layers.append(l)

        ### Remember View
        self.view = context.space_data
        self.pivot_point = self.view.pivot_point
        self.cursor_loc_x = self.view.cursor_location[0]
        self.cursor_loc_y = self.view.cursor_location[1]
        self.cursor_loc_z = self.view.cursor_location[2]

        ### Remember Object
        self.obj = context.object
        self.obj_mode = self.obj.mode
        self.active_shape_key_index = self.obj.active_shape_key_index

        ### Remember rig
        self.arm_obj = None

        # Search for armature modifier
        arm_mods = [mod for mod in self.obj.modifiers if mod.type == 'ARMATURE']
        if arm_mods:
            mod = arm_mods[0]
            self.arm_obj = mod.object

        # Search for armature parents
        if not arm_mods:
            if self.obj.parent_bone:
                self.arm_obj = self.obj.parent

        if self.arm_obj:
            self.pose_position = self.arm_obj.data.pose_position
            
        ### Remember Mesh
        self.mesh = self.obj.data

        # Remember shape keys
        self.shape_keys_values = {}
        if self.mesh.shape_keys:
            for kb in self.mesh.shape_keys.key_blocks:
                self.shape_keys_values[kb.name] = kb.value

        ### Remember Tools Settings
        self.tool_settings = context.tool_settings
        self.mesh_select_mode = []
        self.mesh_select_mode.append(self.tool_settings.mesh_select_mode[0])
        self.mesh_select_mode.append(self.tool_settings.mesh_select_mode[1])
        self.mesh_select_mode.append(self.tool_settings.mesh_select_mode[2])

    def recover(self):
        ### Recover Scene
        # Recover selection
        self.scene.objects.active = self.active_object
        for obj in self.scene.objects:
            if obj in self.selects:
                obj.select = self.selects[obj.name]
                obj.hide = self.hides[obj.name]

        # Recover mode
        if self.active_object and common.in_active_layers(self.active_object):
            bpy.ops.object.mode_set(mode=self.active_object_mode)

        # Recover layers
        for i, l in enumerate(self.layers):
            self.scene.layers[i] = l

        ### Recover View
        self.view.pivot_point = self.pivot_point
        self.view.cursor_location[0] = self.cursor_loc_x
        self.view.cursor_location[1] = self.cursor_loc_y
        self.view.cursor_location[2] = self.cursor_loc_z

        ### Recover Object
        self.obj.active_shape_key_index = self.active_shape_key_index
        bpy.ops.object.mode_set(mode=self.obj_mode)

        ### Recover rig
        if self.arm_obj:
            self.arm_obj.data.pose_position = self.pose_position

        ### Recover Mesh
        # Revert shape keys
        if self.mesh.shape_keys:
            for name, value in self.shape_keys_values.items():
                kb = self.mesh.shape_keys.key_blocks.get(name)
                if kb: kb.value = value

        ### Recover Tools Settings
        self.tool_settings.mesh_select_mode = (
                self.mesh_select_mode[0],
                self.mesh_select_mode[1],
                self.mesh_select_mode[2]
                )

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH' and context.space_data.type == 'VIEW_3D'

    def execute(self, context):
        
        scene = context.scene
        obj = context.object
        view = context.space_data

        self.remember(context)

        # Dealing with shape keys first
        shape_keys_copy = False
        if obj.data.shape_keys and len(obj.data.shape_keys.key_blocks) > 1:
            shape_keys_copy = True

            # Use basis shape
            obj.active_shape_key_index = 0

        # Go to object mode and deselect all objects first
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        # Select the object
        #obj.select = True

        # Set cursor location for mirror pivot
        view.cursor_location = obj.location
        view.pivot_point = 'CURSOR'

        # Go to edit mode
        bpy.ops.object.mode_set(mode='EDIT')

        # Unhide all verts
        bpy.ops.mesh.reveal()
        #obj.data.update()

        # Use face select to detect face midpoint
        bpy.ops.mesh.select_mode(type="FACE")
        bpy.ops.mesh.select_all(action='DESELECT')
        bm = bmesh.from_edit_mesh(obj.data)

        if self.mode == 'X_PLUS_MIN':
            for f in bm.faces:
                if f.calc_center_median().x < 0.0:
                    f.select = True
        elif self.mode == 'X_MIN_PLUS':
            for f in bm.faces:
                if f.calc_center_median().x > 0.0:
                    f.select = True
        elif self.mode == 'Y_PLUS_MIN':
            for f in bm.faces:
                if f.calc_center_median().y < 0.0:
                    f.select = True
        elif self.mode == 'Y_MIN_PLUS':
            for f in bm.faces:
                if f.calc_center_median().y > 0.0:
                    f.select = True
        elif self.mode == 'Z_PLUS_MIN':
            for f in bm.faces:
                if f.calc_center_median().z < 0.0:
                    f.select = True
        elif self.mode == 'Z_MIN_PLUS':
            for f in bm.faces:
                if f.calc_center_median().z > 0.0:
                    f.select = True

        #return {'FINISHED'}
        select_len = len([f for f in bm.faces if f.select])

        # If all faces is selected
        if len(bm.faces) == select_len or select_len == 0:
            bpy.ops.object.mode_set(mode='OBJECT')
            self.report({'WARNING'}, "This object is not valid to mirror, try other axis")
            return {'CANCELLED'}

        # If object using armature
        if self.arm_obj:
            self.arm_obj.data.pose_position = 'REST'

        if shape_keys_copy:
            # Separate mesh for preserving the shape keys
            bpy.ops.mesh.separate(type='SELECTED')
            # The leftover mesh is only selected mesh and deselect it
            left_obj = [o for o in scene.objects if o.select and common.in_active_layers(o) and not o.hide][0]

            # Apply leftover object transform
            bpy.ops.object.mode_set(mode='OBJECT')
            scene.objects.active = left_obj
            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
            left_obj.select = False

            # Sort mesh elements on leftover object
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.sort_elements(type='CURSOR_DISTANCE', elements={'VERT'})
            bpy.ops.object.mode_set(mode='OBJECT')
        else:
            bpy.ops.mesh.delete(type='FACE')

        # Back to main object
        scene.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')

        # Update bmesh because number verts is changed
        #bmesh.update_edit_mesh(obj.data, True)
        bm = bmesh.from_edit_mesh(obj.data)

        for f in bm.faces:
            f.select = True

        # Duplicate and separate mesh
        bpy.ops.mesh.duplicate()
        bpy.ops.mesh.separate(type='SELECTED')

        # Go out of the edit mode
        bpy.ops.object.mode_set(mode='OBJECT')

        # Get the separated object, the only selected object
        mir_obj = [o for o in scene.objects if o.select and common.in_active_layers(o) and not o.hide][0]
        scene.objects.active = mir_obj

        # Mirror the object
        if self.mode in {'X_PLUS_MIN', 'X_MIN_PLUS'}:
            bpy.ops.transform.mirror(constraint_axis=(True, False, False), constraint_orientation='GLOBAL')
        elif self.mode in {'Y_PLUS_MIN', 'Y_MIN_PLUS'}:
            bpy.ops.transform.mirror(constraint_axis=(False, True, False), constraint_orientation='GLOBAL')
        elif self.mode in {'Z_PLUS_MIN', 'Z_MIN_PLUS'}:
            bpy.ops.transform.mirror(constraint_axis=(False, False, True), constraint_orientation='GLOBAL')

        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

        if shape_keys_copy:

            # Delete the shapes because it'll copy from the mesh leftover
            bpy.ops.object.shape_key_remove(all=True)

            # Sort mesh elements on mirror object
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.sort_elements(type='CURSOR_DISTANCE', elements={'VERT'})
            bpy.ops.object.mode_set(mode='OBJECT')

            # Check the same faces between leftover object to mirror object
            similar_face_ids = self.check_similar(left_obj, mir_obj)

            # Select similar faces on mirror object
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bm = bmesh.from_edit_mesh(mir_obj.data)
            bm.faces.ensure_lookup_table()
            for i in similar_face_ids[mir_obj.name]:
                bm.faces[i].select = True

            # Separate the the similar faces for copying shape keys
            bpy.ops.mesh.separate(type='SELECTED')
            mir_obj.select = False
            mir_obj_similar = [o for o in scene.objects if o.select and common.in_active_layers(o) and not o.hide][0]
            mir_obj_similar.select = False

            bpy.ops.object.mode_set(mode='OBJECT')

            # Sort similar mirror object
            scene.objects.active = left_obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.sort_elements(type='CURSOR_DISTANCE', elements={'VERT'})
            bpy.ops.object.mode_set(mode='OBJECT')

            # Delete non similar faces on leftover object
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bm = bmesh.from_edit_mesh(left_obj.data)
            bm.faces.ensure_lookup_table()
            for i in similar_face_ids[left_obj.name]:
                bm.faces[i].select = False
            bpy.ops.mesh.delete(type='FACE')
            # Resort the vertices
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.sort_elements(type='CURSOR_DISTANCE', elements={'VERT'})
            bpy.ops.object.mode_set(mode='OBJECT')

            # Transfer shape keys
            left_obj.select = True
            mir_obj_similar.select = True
            scene.objects.active = mir_obj_similar
            for i, kb in enumerate(left_obj.data.shape_keys.key_blocks):
                if i == 0: continue
                left_obj.active_shape_key_index = i
                bpy.ops.object.shape_key_transfer()
                mir_obj_similar.show_only_shape_key = False

            # Make basis shape as active
            mir_obj_similar.active_shape_key_index = 0

            # Delete leftover object
            mir_obj_similar.select = False
            scene.objects.active = left_obj
            bpy.ops.object.delete()

            # Select all vertex on original mirror but nothing on similar mirror object
            # This is hack so shape keys will not messed up when merging
            scene.objects.active = mir_obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            scene.objects.active = mir_obj_similar
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

            # Merge with the original mirror object
            mir_obj_similar.select = True
            mir_obj.select = True
            scene.objects.active = mir_obj
            bpy.ops.object.join()

            #return {'FINISHED'}

            # Remove doubles
            bpy.ops.object.mode_set(mode='EDIT')
            #bpy.ops.mesh.select_all(action='SELECT')
            #bpy.ops.mesh.remove_doubles()
            bpy.ops.mesh.remove_doubles(use_unselected=True)
            bpy.ops.object.mode_set(mode='OBJECT')

        #return {'FINISHED'}

        # Flip the vertex groups
        self.flip_vertex_group(mir_obj)

        # Merge objects
        bpy.ops.object.select_all(action='DESELECT')
        mir_obj.select = True
        obj.select = True
        scene.objects.active = obj
        bpy.ops.object.join()

        # Go to edit mode again
        bpy.ops.object.mode_set(mode='EDIT')

        # Remove doubles
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()

        # Fix normals
        bpy.ops.mesh.normals_make_consistent(inside=False)

        bpy.ops.mesh.select_all(action='DESELECT')

        bpy.ops.object.mode_set(mode='OBJECT')

        self.recover()

        return {'FINISHED'}

class ShapeKeyMirror(bpy.types.Operator):
    bl_idname = "mesh.shape_key_mirror"
    bl_label = "Mirror Shape Key"
    bl_description = "Mirror shape key value on selected vertices"
    bl_options = {'REGISTER', 'UNDO'}

    def loop_mirror(self, ids):
        for i in ids:
            self.bm.verts[i].select = True
        
            bpy.ops.mesh.select_mirror()
            
            #print(i)
            
            mir_ids = [v.index for v in self.bm.verts if v.select and v.index != i]
            #print(mir_ids)
            
            if mir_ids:
                self.pair_ids[i] = mir_ids[0]
                self.bm.verts[mir_ids[0]].select = False
            else:
                self.bm.verts[i].select = False

    def refresh_bmesh(self, mesh):
        self.bm = bmesh.from_edit_mesh(mesh)
        self.bm.verts.ensure_lookup_table()

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT' and obj.data.shape_keys

    def execute(self, context):
        obj = context.object
        mesh = obj.data
        settings = context.tool_settings

        # Go to object mode to get selection
        bpy.ops.object.mode_set(mode='OBJECT')

        # Remember some value
        ori_use_mirror_x = mesh.use_mirror_x
        ori_use_mirror_topology = mesh.use_mirror_topology
        ori_key_index = obj.active_shape_key_index

        # Remember selection mode
        ori_select_mode = []
        ori_select_mode.append(settings.mesh_select_mode[0])
        ori_select_mode.append(settings.mesh_select_mode[1])
        ori_select_mode.append(settings.mesh_select_mode[2])

        # Remember selection index
        ori_verts = [i for i, v in enumerate(mesh.vertices) if v.select]
        ori_edges = [i for i, e in enumerate(mesh.edges) if e.select]
        ori_polys = [i for i, p in enumerate(mesh.polygons) if p.select]

        # Should be on vertex selection mode
        settings.mesh_select_mode = (True, False, False)

        # Back to edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        self.refresh_bmesh(mesh)

        # Try topology mirror first
        mesh.use_mirror_x = True
        mesh.use_mirror_topology = True

        key = obj.active_shape_key
        #key_val = self.bm.verts.layers.shape.get(key.name)

        #print()

        # Populate mirror indices
        sel_ids = [v.index for v in mesh.vertices if v.select]
        #print(sel_ids)
        bpy.ops.mesh.select_all(action='DESELECT')

        self.pair_ids = {}

        # Iterate mirror to each vertices to get pair vertices
        self.loop_mirror(sel_ids)

        #print(self.pair_ids)

        # If there are some vertices still remains unpaired
        if len(self.pair_ids) != len(sel_ids):
            # Remaining indices not yet paired
            rem_ids = [i for i in sel_ids if i not in self.pair_ids]
            #print(rem_ids)
        
            # Try to mirror with no topology
            mesh.use_mirror_topology = False
            obj.active_shape_key_index = 0
            self.refresh_bmesh(mesh)

            # Reiterate mirror
            self.loop_mirror(rem_ids)

            obj.active_shape_key_index = ori_key_index
            self.refresh_bmesh(mesh)

        #print(self.pair_ids)

        # Got to object mode to edit shapekey data
        bpy.ops.object.mode_set(mode='OBJECT')

        # Edit shape key data
        for i, mir_i in self.pair_ids.items():
            co = key.data[i].co
            key.data[mir_i].co.x = -co.x
            key.data[mir_i].co.y = co.y
            key.data[mir_i].co.z = co.z

        # Recover mirror setting
        mesh.use_mirror_x = ori_use_mirror_x
        mesh.use_mirror_topology = ori_use_mirror_topology

        # Recover selection
        settings.mesh_select_mode = (ori_select_mode[0], ori_select_mode[1], ori_select_mode[2])

        # Reselect stuff
        for i in ori_verts:
            mesh.vertices[i].select = True
        for i in ori_edges:
            mesh.edges[i].select = True
        for i in ori_polys:
            mesh.polygons[i].select = True

        # Finally go back to edit mode
        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}

class ShapeKeyReset(bpy.types.Operator):
    bl_idname = "mesh.shape_key_reset"
    bl_label = "Reset Shape Key"
    bl_description = "Reset shape key value on selected vertices"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type == 'MESH' and obj.mode == 'EDIT' and obj.data.shape_keys

    def execute(self, context):

        #bpy.ops.object.mode_set(mode='OBJECT')

        obj = context.object
        mesh = obj.data
        key = obj.active_shape_key

        #bpy.ops.object.mode_set(mode='EDIT')

        #bm = bmesh.new()
        #bm.from_mesh(mesh)
        #bm.verts.ensure_lookup_table()

        #for i, v in enumerate(bm.verts):
        #    if not v.select: continue
        #    print(i, v.index)
        #    val = bm.verts.layers.shape.get(key.name) 
        #    print(val, v[val], v.co)
        #    v[val].x = v.co.x
        #    v[val].y = v.co.y
        #    v[val].z = v.co.z

        bpy.ops.object.mode_set(mode='OBJECT')

        for i, v in enumerate(mesh.vertices):
            if v.select:
                #print(i, key.data[i].co, v.co)
                key.data[i].co.x = v.co.x
                key.data[i].co.y = v.co.y
                key.data[i].co.z = v.co.z

        bpy.ops.object.mode_set(mode='EDIT')

        return {'FINISHED'}

class FlipMirrorModifier(bpy.types.Operator):
    bl_idname = "mesh.flip_mirror_modifier"
    bl_label = "Flip Mirror Modifier"
    bl_description = "Flip Mirror Modifier"
    bl_options = {'REGISTER', 'UNDO'}

    def revert(self, context):
        bpy.ops.object.mode_set(mode=self.mode)

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'

    def execute(self, context):
        obj = context.object

        self.mode = obj.mode

        # Go to object mode to get selection
        bpy.ops.object.mode_set(mode='OBJECT')

        # Get mirror modifier
        mod = None
        mod_idx = -1
        for i, m in enumerate(obj.modifiers):
            if m.type == 'MIRROR':
                mod = m
                mod_idx = i
                break

        # Check if mirror modifier is first or not
        if mod_idx != 0:
            self.revert(context)
            self.report({'ERROR'}, "Need mirror modifier and it must be first")
            return {'CANCELLED'}

        # Check if mirror modifier has only one axis
        axis = [mod.use_x, mod.use_y, mod.use_z]
        axis_num = 0
        for a in axis:
            if a: axis_num += 1
        if axis_num > 1 or axis_num == 0:
            self.revert(context)
            self.report({'ERROR'}, "Can only flip with only one axis")
            return {'CANCELLED'}

        # Remember selection
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        sel_verts = [i for i, v in enumerate(bm.verts) if v.select]
        sel_edges = [i for i, e in enumerate(bm.edges) if e.select]
        sel_faces = [i for i, f in enumerate(bm.faces) if f.select]

        active_vert = bmesh_vert_active(bm)
        if active_vert: active_vert = active_vert.index

        active_edge = bmesh_edge_active(bm)
        if active_edge: active_edge = active_edge.index

        active_face = bm.faces.active
        if active_face: active_face = active_face.index

        bpy.ops.object.mode_set(mode='OBJECT')

        # Remember some variable
        self.use_mirror_merge = mod.use_mirror_merge
        self.use_clip = mod.use_clip
        self.use_mirror_vertex_groups = mod.use_mirror_vertex_groups
        self.use_mirror_u = mod.use_mirror_u
        self.use_mirror_v = mod.use_mirror_v
        self.mirror_object = mod.mirror_object

        # Disable merge and clip before applying
        mod.use_mirror_merge = False
        mod.use_clip = False

        # Get number of vertices
        num_verts = len(obj.data.vertices)

        # Apply mirror modifier
        bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod.name)

        # Go to edit mode to delete half
        bpy.ops.object.mode_set(mode='EDIT')

        # Get bmesh
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        # Deselect all first
        bpy.ops.mesh.select_all(action='DESELECT')

        # Select all with index below num of verts before applying
        for i in range(0, num_verts):
            bm.verts[i].select = True

        # Delete half
        bpy.ops.mesh.delete(type='VERT')

        # Reselect
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        for i in sel_verts:
            bm.verts[i].select = True
        for i in sel_edges:
            bm.edges[i].select = True
        for i in sel_faces:
            bm.faces[i].select = True
        if active_vert:
            bm.select_history.add(bm.verts[active_vert])
        if active_edge:
            bm.select_history.add(bm.edges[active_edge])
        if active_face:
            bm.faces.active = bm.faces[active_face]

        # Bring back modifier
        bpy.ops.object.modifier_add(type='MIRROR')

        # Move up new mirror modifier
        new_mod = obj.modifiers[-1]
        for i in range(len(obj.modifiers) - 1):
            bpy.ops.object.modifier_move_up(modifier = new_mod.name)

        # Bring back modifier attributes
        new_mod.use_x = axis[0]
        new_mod.use_y = axis[1]
        new_mod.use_z = axis[2]
        new_mod.use_mirror_merge = self.use_mirror_merge
        new_mod.use_clip = self.use_clip
        new_mod.use_mirror_vertex_groups = self.use_mirror_vertex_groups
        new_mod.mirror_object = self.mirror_object

        self.revert(context)

        return {'FINISHED'}

#class MirrorUV(bpy.types.Operator):
#    bl_idname = "mesh.mirror_uv"
#    bl_label = "Flip Mirror Modifier"
#    bl_description = "Flip Mirror Modifier"
#    bl_options = {'REGISTER', 'UNDO'}
#
#    @classmethod
#    def poll(cls, context):
#        return context.object and context.object.type == 'MESH'
#
#    def execute(self, context):
#        return {'FINISHED'}

def register():
    pass

def unregister():
    pass
