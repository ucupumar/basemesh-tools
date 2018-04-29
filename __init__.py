bl_info = {
    "name": "Basemesh Tools",
    "author": "Yusuf Umar",
    "version": (0, 1, 1),
    "blender": (2, 77, 0),
    "location": "View 3D > Tool Shelf > Basemesh",
    "description": "More sophisticated basemesh for sculpt and stuff",
    "wiki_url": "https://github.com/ucupumar/basemesh-tools",
    "category": "Mesh",
}

if "bpy" in locals():
    import imp
    imp.reload(mirror_tools)
    imp.reload(common)
else:
    from . import mirror_tools, common

import bpy, time, math
from bpy.props import FloatProperty, BoolProperty, IntProperty, EnumProperty, StringProperty, PointerProperty
from mathutils import Matrix

# BUGS:
# - Apply metarig mirror pivot / object origin error

extra_exception = [
    'DEF-upper_arm.02.L',
    'DEF-upper_arm.02.R',
    
    'DEF-forearm.02.L',
    'DEF-forearm.02.R',
    
    'DEF-thumb.01.L.02',
    'DEF-thumb.01.R.02',
    
    'DEF-f_index.01.L.02',
    'DEF-f_index.01.R.02',
    
    'DEF-f_middle.01.L.02',
    'DEF-f_middle.01.R.02',
    
    'DEF-f_ring.01.L.02',
    'DEF-f_ring.01.R.02',
    
    'DEF-f_pinky.01.L.02',
    'DEF-f_pinky.01.R.02',
    
    'DEF-thigh.02.L',
    'DEF-thigh.02.R',
    
    'DEF-shin.02.L',
    'DEF-shin.02.R',

    'heel.L',
    'heel.R',

    'heel.02.L',
    'heel.02.R'
]

def_names = { 'hips' : 'DEF-hips',
         'spine' : 'DEF-spine',
         'chest' : 'DEF-chest',
         'neck' : 'DEF-neck',
         'head' : 'DEF-head',
         
         'shoulder.L' : 'DEF-shoulder.L',
         'shoulder.R' : 'DEF-shoulder.R',
         
         'upper_arm.L' : 'DEF-upper_arm.01.L',
         'upper_arm.R' : 'DEF-upper_arm.01.R',
         
         'forearm.L' : 'DEF-forearm.01.L',
         'forearm.R' : 'DEF-forearm.01.R',
         
         'hand.L' : 'DEF-hand.L',
         'hand.R' : 'DEF-hand.R',
         
         'palm.01.L' : 'DEF-palm.01.L',
         'palm.02.L' : 'DEF-palm.02.L',
         'palm.03.L' : 'DEF-palm.03.L',
         'palm.04.L' : 'DEF-palm.04.L',
         
         'palm.01.R' : 'DEF-palm.01.R',
         'palm.02.R' : 'DEF-palm.02.R',
         'palm.03.R' : 'DEF-palm.03.R',
         'palm.04.R' : 'DEF-palm.04.R',
         
         'thumb.01.L' : 'DEF-thumb.01.L.01',
         'thumb.02.L' : 'DEF-thumb.02.L',
         'thumb.03.L' : 'DEF-thumb.03.L',
         
         'thumb.01.R' : 'DEF-thumb.01.R.01',
         'thumb.02.R' : 'DEF-thumb.02.R',
         'thumb.03.R' : 'DEF-thumb.03.R',
         
         'f_index.01.L' : 'DEF-f_index.01.L.01',
         'f_index.02.L' : 'DEF-f_index.02.L',
         'f_index.03.L' : 'DEF-f_index.03.L',
         
         'f_index.01.R' : 'DEF-f_index.01.R.01',
         'f_index.02.R' : 'DEF-f_index.02.R',
         'f_index.03.R' : 'DEF-f_index.03.R',
         
         'f_middle.01.L' : 'DEF-f_middle.01.L.01',
         'f_middle.02.L' : 'DEF-f_middle.02.L',
         'f_middle.03.L' : 'DEF-f_middle.03.L',
         
         'f_middle.01.R' : 'DEF-f_middle.01.R.01',
         'f_middle.02.R' : 'DEF-f_middle.02.R',
         'f_middle.03.R' : 'DEF-f_middle.03.R',
         
         'f_ring.01.L' : 'DEF-f_ring.01.L.01',
         'f_ring.02.L' : 'DEF-f_ring.02.L',
         'f_ring.03.L' : 'DEF-f_ring.03.L',
         
         'f_ring.01.R' : 'DEF-f_ring.01.R.01',
         'f_ring.02.R' : 'DEF-f_ring.02.R',
         'f_ring.03.R' : 'DEF-f_ring.03.R',
         
         'f_pinky.01.L' : 'DEF-f_pinky.01.L.01',
         'f_pinky.02.L' : 'DEF-f_pinky.02.L',
         'f_pinky.03.L' : 'DEF-f_pinky.03.L',
         
         'f_pinky.01.R' : 'DEF-f_pinky.01.R.01',
         'f_pinky.02.R' : 'DEF-f_pinky.02.R',
         'f_pinky.03.R' : 'DEF-f_pinky.03.R',
         
         'thigh.L' : 'DEF-thigh.01.L',
         'thigh.R' : 'DEF-thigh.01.R',
         
         'shin.L' : 'DEF-shin.01.L',
         'shin.R' : 'DEF-shin.01.R',
         
         'foot.L' : 'DEF-foot.L',
         'foot.R' : 'DEF-foot.R',
         
         'toe.L' : 'DEF-toe.L',
         'toe.R' : 'DEF-toe.R'
       }

# Potentially cause DAG zero error
def make_layers_active(obj):
    sce = bpy.context.scene
    for i, l in enumerate(obj.layers):
        if l and not sce.layers[i]: sce.layers[i] = True

def in_active_armature_layers(arm, bone):
    return any([l for i, l in enumerate(bone.layers) if l and arm.layers[i]])

def make_armature_layers_active(arm, bone):
    for i, l in enumerate(bone.layers):
        if l: arm.layers[i] = True

def no_active_object_error_prevention():
    scene = bpy.context.scene
    obj = bpy.context.object
    if obj:
        # Return true if there's active object
        return True
    else:
        # Search for any object in active layer and set it to active object
        for o in scene.objects:
            if common.in_active_layers(o):
                scene.objects.active = o
                return True
        # Return false if any object is not found
        return False

def remember(object_action = False, remember_metarig = True):
    scene = bpy.context.scene
    props = scene.basemesh_tools_props

    global ori_selects
    global ori_active
    global ori_scene_layers
    global ori_object_layers
    global ori_object_mode
    global ori_object_hides
    global ori_object_actions
    global ori_rig_layers
    global ori_rig_bone_hides
    global ori_rig_bone_hide_selects
    global ori_rig_bone_matrices
    #global ori_selected_bones
    #global ori_active_bones
    
    ori_selects = [o for o in bpy.context.selected_objects]
    ori_active = scene.objects.active

    ori_scene_layers = [l for l in scene.layers]
    ori_object_layers = {}
    for o in scene.objects:
        ori_object_layers[o.name] = [l for l in o.layers]

    ori_object_mode = {}
    for o in scene.objects:
        ori_object_mode[o.name] = o.mode

    ori_object_hides = []
    for o in scene.objects:
        if o.hide:
            ori_object_hides.append(o.name)

    #ori_object_actions = {}
    #for o in scene.objects:
    #    if o.animation_data and o.animation_data.action:
    #        ori_object_actions[o.name] = o.animation_data.action

    ori_rig_layers = {}
    ori_rig_bone_hides = {}
    ori_rig_bone_hide_selects = {}
    ori_rig_bone_matrices = {}

    for o in scene.objects:
        if o.type == 'ARMATURE':

            if not remember_metarig and o == scene.objects.get(props.metarig_object):
                continue

            hides = {}
            hide_selects = {}
            matrices = {}

            for bone in o.data.bones:
                hides[bone.name] = bone.hide
                hide_selects[bone.name] = bone.hide_select
                #if not any([prefix for prefix in {'DEF-', 'MCH-', 'ORG-'} if prefix in bone.name]):
                pose_bone = o.pose.bones.get(bone.name)
                matrices[bone.name] = pose_bone.matrix_basis.copy()

            ori_rig_bone_hides[o.name] = hides
            ori_rig_bone_hide_selects[o.name] = hide_selects
            ori_rig_bone_matrices[o.name] = matrices
            ori_rig_layers[o.name] = [l for l in o.data.layers]

def revert():
    scene = bpy.context.scene

    # Revert selection
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')

    for o in ori_selects:
        o.select = True

    # Revert mode
    for name, mode in ori_object_mode.items():
        o = scene.objects.get(name)
        if o and common.in_active_layers(o) and o.mode != mode:
            scene.objects.active = o
            bpy.ops.object.mode_set(mode=mode)
        
    # Revert active
    if ori_active:
        scene.objects.active = ori_active
        #bpy.ops.object.mode_set(mode=ori_mode)

    # Revert scene layers
    for i, l in enumerate(ori_scene_layers):
        scene.layers[i] = l

    # Revert object layers
    for name, layers in ori_object_layers.items():
        o = scene.objects.get(name)
        if o:
            for i, l in enumerate(layers):
                if o.layers[i] != l:
                    o.layers[i] = l

    # Revert rig layers
    #print('aaaaaaaa')
    for name, layers in ori_rig_layers.items():
        o = scene.objects.get(name)
        if o:
            #print(o.name)
            for i, l in enumerate(layers):
                if o.data.layers[i] != l:
                    o.data.layers[i] = l

    # Revert object hide
    for name in ori_object_hides:
        o = scene.objects.get(name)
        if o:
            o.hide = True

    # Revert object anim
    #for name, action in ori_object_actions.items():
    #    o = scene.objects.get(name)
    #    if o:
    #        o.animation_data.action = action

    # Revert bone hide
    for name, hides in ori_rig_bone_hides.items():
        o = scene.objects.get(name)
        if o and o.type == 'ARMATURE':
            hide_selects = ori_rig_bone_hide_selects[name]
            for bone_name, hide in hides.items():
                bone = o.data.bones.get(bone_name)
                if bone:
                    bone.hide = hide
                    bone.hide_select = hide_selects[bone_name]

    # Revert bone matrices
    for name, matrices in ori_rig_bone_matrices.items():
        o = scene.objects.get(name)
        if o and o.type == 'ARMATURE':
            for bone_name, matrix in matrices.items():
                pbone = o.pose.bones.get(bone_name)
                if pbone:
                    pbone.matrix_basis = matrix

# This function assume only object is active, selected and on object mode
# The return is same state
def create_shape_keys_objects(obj):
    scene = bpy.context.scene
    props = scene.basemesh_tools_props
    metarig_obj = scene.objects.get(props.metarig_object)

    # Deselect other objects and select only current object
    bpy.ops.object.select_all(action='DESELECT')
    obj.select = True
    scene.objects.active = obj

    key_objs = []
    for i, kb in enumerate(obj.data.shape_keys.key_blocks):
        if i == 0: continue

        #print('KB_NAME:', kb.name)
        #print('OBJ:', obj)

        # Duplicate the object
        bpy.ops.object.duplicate()
        dup_obj = scene.objects.active
        dup_obj.name = kb.name + '__' + obj.name
        #print('DUPNAME: ' + dup_obj.name)

        dup_obj.show_only_shape_key = False

        # Clear shape key influence
        bpy.ops.object.shape_key_clear()
        dup_obj.active_shape_key_index = i
        key = dup_obj.active_shape_key

        print('Begin removing', dup_obj.name, 'shape keys')

        # Copy current shape key value to mesh data
        for j, v in enumerate(dup_obj.data.vertices):
            v.co.x = key.data[j].co.x
            v.co.y = key.data[j].co.y
            v.co.z = key.data[j].co.z

        # Set only this key as 1.0 on delete other keys on duplicated object
        #for j, dkb in reversed(list(enumerate(dup_obj.data.shape_keys.key_blocks))):
        #    if j == i:
        #        dkb.value = 1.0
        #    #else: dkb.value = 0.0
        #    else:
        #        dup_obj.active_shape_key_index = j
        #        bpy.ops.object.shape_key_remove(all=False)

        ## The last key should be deleted too
        #bpy.ops.object.shape_key_remove(all=False)
        bpy.ops.object.shape_key_remove(all=True)

        print('Begin apply', dup_obj.name, 'modifiers')

        # Apply the modifiers
        for mod in dup_obj.modifiers:
            if mod.type == 'ARMATURE' and mod.object in {metarig_obj}:
                bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod.name)

        dup_obj.select = False
        obj.select = True
        scene.objects.active = obj

        key_objs.append(dup_obj)

    # Set all keys on main object as 0.0
    for i, kb in enumerate(obj.data.shape_keys.key_blocks):
        if i == 0: continue
        kb.value = 0.0

    # Delete all shape keys on main object
    bpy.ops.object.shape_key_remove(all=True)

    return key_objs

# This function assume only object is active, selected and on object mode
# The return is same state
def shape_keys_recover(obj, key_objs, first_key_name):
    # Add basis key first
    bpy.ops.object.shape_key_add(from_mix = False)

    # Recover shape key from key objects
    for ko in key_objs:
        #print(ko.name)
        ko.select = True
        bpy.ops.object.join_shapes()

        # Delete key object
        obj.select = False
        bpy.ops.object.delete(use_global=False)
        obj.select = True

    for i, kb in enumerate(obj.data.shape_keys.key_blocks):
        if i == 0:
            kb.name = first_key_name
            continue

        splitted = kb.name.split('__')
        kb.name = splitted[0]

def is_matrix_close(matrix_a, matrix_b, rel_tol=1e-02):
    for i, vec in enumerate(matrix_a):
        for j, val in enumerate(vec):
            if not math.isclose(val, matrix_b[i][j], rel_tol=rel_tol):
                return False
    return True

class ApplyMetarigTransform(bpy.types.Operator):
    """Apply metarig transform"""
    bl_idname = "mesh.apply_metarig_transform"
    bl_label = "Apply Metarig Transform"
    bl_options = {'REGISTER', 'UNDO'}

    symmetrize = BoolProperty(name='Symmetrize Rig', default=True)
    force_default_metarig_param = BoolProperty(name='Force Default Rigify Param', default=True)

    @classmethod
    def poll(cls, context):
        scene = context.scene
        props = context.scene.basemesh_tools_props
        metarig_obj = scene.objects.get(props.metarig_object)
        return metarig_obj
        #return True

    def execute(self, context):
        scene = context.scene
        props = scene.basemesh_tools_props
        metarig_obj = scene.objects.get(props.metarig_object)
        rigify_obj = scene.objects.get(props.rigify_object)

        # This script need rigify legacy mode, so activate one if doesn't already
        original_legacy_mode = context.user_preferences.addons['rigify'].preferences.legacy_mode
        context.user_preferences.addons['rigify'].preferences.legacy_mode = True

        remember(remember_metarig = False)

        if not no_active_object_error_prevention():
            self.report({'WARNING'}, "No object found in this layer!")
            return {'CANCELLED'}

        # Make sure everyone not using rigify
        #bpy.ops.mesh.toggle_metarig_rigify(convert_type='TO_METARIG')

        # Make metarig object layer active
        if not common.in_active_layers(metarig_obj):
            make_layers_active(metarig_obj)

        # Populate list of transformed bones
        transformed_bone_names = []
        for pose_bone in metarig_obj.pose.bones:
            if pose_bone.matrix_basis != Matrix():
                transformed_bone_names.append(pose_bone.name)

        # Symmetrize rig
        if self.symmetrize:

            # Make metarig active and deselect all bones
            scene.objects.active = metarig_obj
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.select_all(action='DESELECT')

            for bone_name in transformed_bone_names:

                # Make bone active
                bone = metarig_obj.data.bones.get(bone_name)
                bone.select = True
                metarig_obj.data.bones.active = bone

                # Mirror it
                bpy.ops.pose.select_mirror()
                mirrored_bone = metarig_obj.data.bones.active

                # Get the childrens
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.armature.select_similar(type='CHILDREN')
                bpy.ops.object.mode_set(mode='POSE')
                mirrored_bone_childrens = [b for b in metarig_obj.data.bones if b.select]

                # Deselect first
                bpy.ops.pose.select_all(action='DESELECT')

                # Copy transform inheritance from original bone children
                for mir_bone in mirrored_bone_childrens:
                    metarig_obj.data.bones.active = mir_bone
                    bpy.ops.pose.select_mirror()
                    ori_bone = metarig_obj.data.bones.active

                    if mir_bone.use_inherit_rotation != ori_bone.use_inherit_rotation:
                        mir_bone.use_inherit_rotation = ori_bone.use_inherit_rotation
                    if mir_bone.use_inherit_scale != ori_bone.use_inherit_scale:
                        mir_bone.use_inherit_scale = ori_bone.use_inherit_scale
                    if mir_bone.use_local_location != ori_bone.use_local_location:
                        mir_bone.use_local_location = ori_bone.use_local_location

                    bpy.ops.pose.select_all(action='DESELECT')

            # Mirror pose
            if transformed_bone_names:
                for bone_name in transformed_bone_names:
                    bone = metarig_obj.data.bones.get(bone_name)
                    metarig_obj.data.bones.active = bone
                    bone.select = True

                bpy.ops.pose.copy()
                bpy.ops.pose.paste(flipped=True)

        # Force metarig parameters to default
        if self.force_default_metarig_param:

            # Create new temporary metarig
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            bpy.ops.object.armature_human_metarig_add()
            temp_metarig = scene.objects.active

            for bone in metarig_obj.pose.bones:
                pair_bone = temp_metarig.pose.bones.get(bone.name)
                if pair_bone:
                    # For now, only match some problematic layers
                    for i, l in enumerate(pair_bone.rigify_parameters.ik_layers):
                        bone.rigify_parameters.ik_layers[i] = l
                    for i, l in enumerate(pair_bone.rigify_parameters.hose_layers):
                        bone.rigify_parameters.hose_layers[i] = l

            # Delete temporary metarig
            temp_arm = temp_metarig.data
            bpy.ops.object.delete(use_global=False)
            bpy.data.armatures.remove(temp_arm, do_unlink=True)
            scene.objects.active = metarig_obj

        # Get matrix basis of all bones
        basis_matrices = {}
        for pb in metarig_obj.pose.bones:
            basis_matrices[pb.name] = pb.matrix_basis.copy()

        # Make the rig use rest pose
        for pb in metarig_obj.pose.bones:
            pb.matrix_basis = Matrix()
        scene.update()

        # Get rest world matrix
        rest_world_matrices = {}
        for pb in metarig_obj.pose.bones:
            rest_world_matrices[pb.name] = pb.matrix.copy()

        # Revert bone to real pose
        for pb in metarig_obj.pose.bones:
            pb.matrix_basis = basis_matrices[pb.name]
        scene.update()

        # Get bones that has transformed world matrix
        transformed_world_bone_names = []
        for pose_bone in metarig_obj.pose.bones:
            #print(pose_bone.name)
            #print(pose_bone.matrix == rest_world_matrices[pose_bone.name])
            if pose_bone.matrix != rest_world_matrices[pose_bone.name]:
                transformed_world_bone_names.append(pose_bone.name)

        # To store modifiers which using rigify
        rigify_modifiers = []
        using_rigify_objects = []

        # Object mode and deselect just in case
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        for o in scene.objects:

            print('Processing', o.name)

            #ori_location = o.location.copy()

            # Search for modifiers to apply
            armature_mod_copies = []
            for i, mod in enumerate(o.modifiers):

                if mod.type != 'ARMATURE': continue
                if not mod.object: continue

                #if o.name == 'Hair':
                #    print('Hair Mod object:', mod.object.name)

                #if mod.object == metarig_obj:
                if mod.object in {metarig_obj, rigify_obj}:

                    mod_copy = {}
                    mod_copy['index'] = i
                    attr_list = dir(mod)
                    for attr in attr_list:
                        if attr.startswith('__') or attr in {'bl_rna', 'rna_type', 'type'}: continue
                        mod_copy[attr] = getattr(mod, attr)
                    armature_mod_copies.append(mod_copy)

                    # Change modifier object temporarily to metarig if using rigify
                    if mod.object == rigify_obj:
                        # Store some temprary variables
                        rigify_modifiers.append(mod)
                        if o not in using_rigify_objects: using_rigify_objects.append(o)

                        # Change vertex groups to metarig
                        for vg in o.vertex_groups:
                            key = [key for key, value in def_names.items() if value == vg.name]
                            if key: vg.name = key[0]

                        # Change modifier to use metarig
                        mod.object = metarig_obj

            #print(o.name)
            #if o.name == 'Hair':
            #    print(armature_mod_copies)
            #    return {'FINISHED'}

            if armature_mod_copies:

                scene.objects.active = o
                # Make the layer active
                if not common.in_active_layers(o):
                    make_layers_active(o)
                # Unhide object
                if o.hide: o.hide = False
                o.select = True
                bpy.ops.object.mode_set(mode='OBJECT')

                # Check if the object has mirror modifier
                mirror_mods = [m for m in o.modifiers if m.type == 'MIRROR']
                need_origin_adjustment = False
                if mirror_mods:
                    print(o.name, 'has mirror modifier!')

                    # Check its object's vertex groups
                    weights = {}
                    for i, vg in enumerate(o.vertex_groups):
                        weights[vg.name] = 0
                        for v in o.data.vertices:
                            for g in v.groups:
                                if g.group == i:
                                    weights[vg.name] += g.weight

                    # Remove very small weights
                    weights = {key:w for key, w in weights.items() if w > 0.9}
                    #print(weights)

                    # Get highest hierarchy bone
                    num_parents = 9999
                    top_bone = None
                    for key, weight in weights.items():
                        pose_bone = metarig_obj.pose.bones.get(key)
                        if pose_bone:
                            parents = pose_bone.parent_recursive
                            if len(parents) < num_parents:
                                num_parents = len(parents)
                                top_bone = pose_bone

                    # If top bone has transformed
                    if top_bone and top_bone.name in transformed_world_bone_names:

                        # For now only sample first mirror mod
                        mirror_mod = mirror_mods[0]
                        if mirror_mod.use_x and o.location[0] == metarig_obj.location[0]:
                            pass
                        elif mirror_mod.use_y and o.location[1] == metarig_obj.location[1]:
                            pass
                        elif mirror_mod.use_z and o.location[2] == metarig_obj.location[2]:
                            pass
                        else:
                            need_origin_adjustment = True
                            print(top_bone.name)

                            #space = context.space_data
                            #space.cursor_location = o.location

                            # Create empty to for origin matrix reference
                            bpy.ops.object.empty_add(type='PLAIN_AXES', radius=0.2, location=o.location)
                            empty = scene.objects.active
                            empty.layers[0] = True
                            empty.name = 'empty_' + o.name
                            empty.rotation_mode = o.rotation_mode
                            empty.rotation_euler = o.rotation_euler.copy()
                            empty.rotation_quaternion = o.rotation_quaternion.copy()
                            empty.scale = o.scale.copy()
                            #empty.select = False

                            #print(empty.name)

                            # Make rig to use rest pose first
                            metarig_obj.data.pose_position = 'REST'
                            scene.update()

                            # Parent empty to top bone
                            bpy.ops.object.select_all(action='DESELECT')
                            empty.select = True
                            metarig_obj.select = True
                            scene.objects.active = metarig_obj
                            bpy.ops.object.mode_set(mode='POSE')
                            #bpy.ops.pose.select_all(action='DESELECT')
                            top_bone_data = metarig_obj.data.bones.get(top_bone.name)
                            #top_bone.select = True
                            metarig_obj.data.bones.active = top_bone_data
                            bpy.ops.object.parent_set(type='BONE')
                            bpy.ops.object.mode_set(mode='OBJECT')
                            bpy.ops.object.select_all(action='DESELECT')

                            # Go back to real pose
                            metarig_obj.data.pose_position = 'POSE'
                            scene.update()

                            # Back to select original object
                            scene.objects.active = o

                            # Rest top bone and all it parents before applying modifier
                            top_bone_parents = top_bone.parent_recursive
                            top_bone.matrix_basis = Matrix()
                            for bone in top_bone_parents:
                                bone.matrix_basis = Matrix()

                            #scene.update()

                # Dealing with shape keys
                shape_keys_found = False
                if o.data.shape_keys:
                    shape_keys_found = True
                    first_key_name = o.data.shape_keys.key_blocks[0].name

                    # Remember state
                    obj_state = common.ObjectState(o)
                    mesh_state = common.MeshState(o.data)

                    key_objs = create_shape_keys_objects(o)

                    #return {'FINISHED'}

                if armature_mod_copies:
                    print('Begin applying armature modifiers of', o.name)

                # Apply the modifiers
                for mod_copy in armature_mod_copies:
                    mod = o.modifiers[mod_copy['index']]
                    bpy.ops.object.modifier_apply(apply_as='DATA', modifier=mod.name)

                if shape_keys_found:
                    print('Begin recover shape keys of', o.name)
                    shape_keys_recover(o, key_objs, first_key_name)

                    # Recover state
                    obj_state.revert()
                    mesh_state.revert()

                    #return {'FINISHED'}

                # If origin adjustment is needed
                if need_origin_adjustment:

                    # Revert bone basis matrix
                    top_bone.matrix_basis = basis_matrices[top_bone.name]
                    for bone in top_bone_parents:
                        bone.matrix_basis = basis_matrices[bone.name]

                    # Clear parent on empty object to get real matrix world
                    bpy.ops.object.select_all(action='DESELECT')
                    empty.select = True
                    scene.objects.active = empty
                    bpy.ops.object.parent_clear(type='CLEAR_KEEP_TRANSFORM')
                    scene.objects.active = o

                    o.matrix_world = empty.matrix_world

                    # Delete empty
                    scene.objects.unlink(empty)
                    bpy.data.objects.remove(empty, do_unlink=True)

                # Add back modifier and set back its attributes
                for mod_copy in armature_mod_copies:
                    # New modifier
                    bpy.ops.object.modifier_add(type='ARMATURE')

                    # Get the new modifier
                    last_idx = len(o.modifiers) - 1
                    mod = o.modifiers[last_idx]

                    # Set the attributes
                    for attr, value in mod_copy.items():
                        if attr != 'index':
                            setattr(mod, attr, value)

                    # Set back the original stack position
                    if last_idx > 0:
                        idx_diff = last_idx - mod_copy['index']
                        for i in range(idx_diff):
                            bpy.ops.object.modifier_move_up(modifier=mod.name)
                #print('safe?')

                #o.select = False
                #if o.name == 'Head':
                #    return {'FINISHED'}

        # Apply metarig to rest pose
        scene.objects.active = metarig_obj
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.armature_apply()

        # Check extra bones
        extra_bones = {}
        for b in metarig_obj.data.bones:
            if b.name not in def_names and b.name not in extra_exception:
                if b.parent:
                    extra_bones[b.name] = b.parent.name
                else: extra_bones[b.name] = ''

        #print(extra_bones)

        # If extra bones found, duplicate metarig
        if extra_bones and rigify_obj:
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            metarig_obj.select = True
            scene.objects.active = metarig_obj

            # Select extra bones
            bpy.ops.object.mode_set(mode='POSE')
            bpy.ops.pose.select_all(action='DESELECT')
            for b in metarig_obj.data.bones:
                if b.name in extra_bones:
                    b.select = True

            # Duplicate metarig for extra bones only rig
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.duplicate()
            extra_bones_only = scene.objects.active
            extra_bones_only.name = '__extra_bones_only'

            # Delete other bones other than extra bones
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.armature.select_all(action='INVERT')
            bpy.ops.armature.delete()
            bpy.ops.object.mode_set(mode='OBJECT')

            # Duplicate the metarig again to get pure metarig
            bpy.ops.object.select_all(action='DESELECT')
            metarig_obj.select = True
            scene.objects.active = metarig_obj
            bpy.ops.object.duplicate()
            pure_metarig = scene.objects.active
            pure_metarig.name = '__pure_metarig'

            # Delete extra bones on pure metarig
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.armature.delete()
            bpy.ops.object.mode_set(mode='OBJECT')

            #return {'FINISHED'}

        # Bring back to rigify objects
        for o in using_rigify_objects:
            for vg in o.vertex_groups:
                if vg.name in def_names:
                    vg.name = def_names[vg.name]

        for mod in rigify_modifiers:
            mod.object = rigify_obj

        # Regenerate rigify
        if rigify_obj:

            # Store original action
            action = rigify_obj.animation_data.action
            # Store original pose
            #pose_matrices = {}
            #for pb in rigify_obj.pose.bones:
            #    pose_matrices[pb.name] = pb.matrix_basis.copy()
            # Store custom properties
            custom_props = {}
            for pb in rigify_obj.pose.bones:
                custom_props[pb.name] = {}
                for key in pb.keys():
                    if key not in {'_RNA_UI', 'rigify_parameters', 'rigify_type'}:
                        custom_props[pb.name][key] = pb[key]

            # Populate modifiers using this rigify object
            mods = []
            for o in scene.objects:
                #if hasattr(o, 'modifiers'):
                for mod in o.modifiers:
                    if mod.type == 'ARMATURE' and mod.object == rigify_obj:
                        mods.append(mod)

            # Populate objects that parent to rigify object
            child_objs = {}
            for o in scene.objects:
                if o.parent == rigify_obj and o.parent_bone:
                    child_objs[o.name] = o.parent_bone

            # Unregister old rig ui script
            script = bpy.data.texts.get("rig_ui.py")
            if script:
                script.write("\nunregister()")
                exec(script.as_string(), {})

            # Set rigify object to active layer and select it
            if not common.in_active_layers(rigify_obj):
                make_layers_active(rigify_obj)
            bpy.ops.object.mode_set(mode='OBJECT')
            bpy.ops.object.select_all(action='DESELECT')
            rigify_obj.select = True
            scene.objects.active = rigify_obj
            bpy.ops.object.mode_set(mode='OBJECT')

            # Delete rigify object
            bpy.ops.object.delete(use_global=False)

            # Reselect metarig
            if extra_bones:
                scene.objects.active = pure_metarig
            else:
                scene.objects.active = metarig_obj

            # Regenerate rigify
            bpy.ops.pose.rigify_generate()

            # Get new rigify object
            rigify_obj = scene.objects.active
            rigify_obj.select = True
            rigify_obj.name = props.rigify_object

            # Dealing with extra bones
            if extra_bones:

                # Delete pure metarig first
                bpy.data.armatures.remove(pure_metarig.data, do_unlink=True)
                bpy.data.objects.remove(pure_metarig, do_unlink=True)

                # Select extra bones only
                extra_bones_only.select = True
                bpy.ops.object.join()
                
                # Reparent extra bones
                bpy.ops.object.mode_set(mode='EDIT')
                for eb, par in extra_bones.items():
                    if par and par in def_names:
                        #bpy.ops.armature.select_all(action='DESELECT')
                        # Get parent bone
                        parent_name = def_names[par]
                        parent_name = parent_name.replace('DEF-', 'ORG-', 1)
                        if [a for a in {'upper_arm', 'forearm', 'thigh', 'shin'} if a in parent_name]:
                            parent_name = parent_name.replace('.01.', '.', 1)
                            parent_name = parent_name.replace('.02.', '.', 1)
                        parent = rigify_obj.data.edit_bones.get(parent_name)
                        #rigify_obj.data.bones.active = parent

                        # Get extra bone
                        extra_bone = rigify_obj.data.edit_bones.get(eb)

                        # Set parent
                        #rigify_obj.data.edit_bones.get(eb).select = True
                        extra_bone.parent = parent

                        # Set layers for FK and IK bones
                        if parent_name in {'ORG-upper_arm.L', 'ORG-forearm.L'}:
                            extra_bone.layers[6] = True
                            extra_bone.layers[7] = True
                        if parent_name in {'ORG-upper_arm.R', 'ORG-forearm.R'}:
                            extra_bone.layers[9] = True
                            extra_bone.layers[10] = True
                        if parent_name in {'ORG-thigh.L', 'ORG-shin.L'}:
                            extra_bone.layers[12] = True
                            extra_bone.layers[13] = True
                        if parent_name in {'ORG-thigh.R', 'ORG-shin.R'}:
                            extra_bone.layers[15] = True
                            extra_bone.layers[16] = True

                        #bpy.ops.armature.parent_set(type='OFFSET')
                bpy.ops.object.mode_set(mode='OBJECT')

            # Set back rigify object to modifiers that use it
            for mod in mods:
                mod.object = rigify_obj

            # Set back parent
            if child_objs:
                scene.objects.active = rigify_obj
                rigify_obj.select = True
                bpy.ops.object.mode_set(mode='POSE')
                bpy.ops.pose.select_all(action='DESELECT')

                for obj_name, bone_name in child_objs.items():

                    # Get the object
                    o = scene.objects.get(obj_name)
                    if o:
                        if not common.in_active_layers(o):
                            make_layers_active(o)
                        o.select = True

                        # Get the bone
                        bone = rigify_obj.data.bones.get(bone_name)
                        
                        if not in_active_armature_layers(rigify_obj.data, bone):
                            make_armature_layers_active(rigify_obj.data, bone)

                        # Parent object to bone
                        rigify_obj.data.bones.active = bone
                        bone.select = True
                        bpy.ops.object.parent_set(type='BONE')
                        bone.select = False

            # Set action back
            if action:
                rigify_obj.animation_data.action = action
            # Set pose matrix back
            #for bone_name, matrix in pose_matrices.items():
            #    pb = rigify_obj.pose.bones.get(bone_name)
            #    if pb and matrix != Matrix():
            #        pb.matrix_basis = matrix
            # Set custom properties back
            for bone_name, props in custom_props.items():
                pb = rigify_obj.pose.bones.get(bone_name)
                #print(bone_name)
                #print(props)
                if pb and props:
                    for prop_name, value in props.items():
                        pb[prop_name] = value

        # Revert state
        revert()

        # Bring back original legacy mode setting
        context.user_preferences.addons['rigify'].preferences.legacy_mode = original_legacy_mode

        #print('Metness')
        return {'FINISHED'}

class MetarigRigifyToggle(bpy.types.Operator):
    """Convert metarig to rigify and vice versa"""
    bl_idname = "mesh.toggle_metarig_rigify"
    bl_label = "Toggle Metarig/Rigify"
    bl_options = {'REGISTER', 'UNDO'}

    convert_type = EnumProperty(
        name = "Convert Type",
        #description="", 
        items=(
            ('AUTO', "Auto", ""),
            ('TO_METARIG', "To Metarig", ""),
            ('TO_RIGIFY', "To Rigify", "")
            ), 
        default='AUTO',
        )

    def modify_shapekeys(self, obj, shapekey_part):
        scene = bpy.context.scene
        props = scene.basemesh_tools_props

        if not obj: return
        if not obj.data: return
        if not hasattr(obj.data, 'shape_keys'): return
        if not obj.data.shape_keys: return

        keys = [key for key in obj.data.shape_keys.key_blocks if shapekey_part in key.name]

        if keys:
            for key in obj.data.shape_keys.key_blocks:
                if key in keys:
                    key.value = 1.0
                else:
                    key.value = 0.0

            # Select the key
            id = [i for i, key in enumerate(obj.data.shape_keys.key_blocks) if key == keys[0]][0]
            obj.active_shape_key_index = id

    @classmethod
    def poll(cls, context):
        scene = context.scene
        props = scene.basemesh_tools_props
        metarig_obj = scene.objects.get(props.metarig_object)
        rigify_obj = scene.objects.get(props.rigify_object)
        return (metarig_obj and metarig_obj.type == 'ARMATURE' and
                rigify_obj and rigify_obj.type == 'ARMATURE')

    def execute(self, context):
        scene = bpy.context.scene
        props = scene.basemesh_tools_props
        objs = [o for o in scene.objects]

        self.metarig_obj = scene.objects.get(props.metarig_object)
        self.rigify_obj = scene.objects.get(props.rigify_object)

        remember()

        if self.convert_type == 'TO_METARIG':
            to_metarig = True
        elif self.convert_type == 'TO_RIGIFY':
            to_metarig = False
        elif self.convert_type == 'AUTO':
            to_metarig = False
            if common.in_active_layers(self.rigify_obj):
                to_metarig = True

        #print(to_metarig)

        if to_metarig:
            source_rig_obj = self.rigify_obj
            target_rig_obj = self.metarig_obj
            target_key = props.metarig_shape_key_name
        else: 
            source_rig_obj = self.metarig_obj
            target_rig_obj = self.rigify_obj
            target_key = props.rigify_shape_key_name

        if not no_active_object_error_prevention():
            self.report({'WARNING'}, "No object found in this layer!")
            return {'CANCELLED'}

        # Deselect objects
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        # Make target rig active
        make_layers_active(target_rig_obj)
        scene.objects.active = target_rig_obj

        # Unhide target rig
        target_rig_obj.hide = False

        bpy.ops.object.mode_set(mode='POSE')

        # Store all matrix first
        #pose_matrices = {}
        #for pb in target_rig_obj.pose.bones:
        #    pose_matrices[pb.name] = pb.matrix_basis.copy()

        # Make all armature layers active
        for i in range(len(target_rig_obj.data.layers)):
            target_rig_obj.data.layers[i] = True

        # Unhide all bones
        for bone in target_rig_obj.data.bones:
            bone.hide = False
        # Make target bones in rest position:
        for pb in target_rig_obj.pose.bones:
            #if not any([prefix for prefix in {'DEF-', 'MCH-', 'ORG-'} if prefix in bone.name]):
            pb.matrix_basis = Matrix()
        for pb in source_rig_obj.pose.bones:
            pb.matrix_basis = Matrix()

        #start_time = time.time()
        #return {'FINISHED'}

        #print(source_rig_obj)

        # Search for object parent to rig
        for o in objs:

            #print(o.name)
            #return {'FINISHED'}

            if o.parent == source_rig_obj and o.parent_bone:

                if not common.in_active_layers(o):
                    #print(o.name)
                    make_layers_active(o)

                #print(o.name)

                o.select = True
                
                target_bone_name = ''
                #start_time = time.time()
                if to_metarig:
                    target_bone_name = [key for key, value in def_names.items() if value == o.parent_bone]
                    if target_bone_name:
                        target_bone_name = target_bone_name[0]
                elif o.parent_bone in def_names:
                    target_bone_name = def_names[o.parent_bone]

                if not target_bone_name or target_bone_name == '':
                    target_bone_name = o.parent_bone

                #print(time.time() - start_time)

                if target_bone_name:
                    
                    #o.parent_bone = target_bone_name
                    target_bone = target_rig_obj.data.bones.get(target_bone_name)
                    
                    #if not in_active_armature_layers(target_rig_obj.data, target_bone):
                    #    make_armature_layers_active(target_rig_obj.data, target_bone)
                    
                    # Select target bone
                    target_bone.select = True
                    target_rig_obj.data.bones.active = target_bone
                    
                    # Parent bone
                    #start_time = time.time()
                    bpy.ops.object.parent_set(type='BONE')
                    #o.matrix_world = target_bone.matrix_local.inverted()
                    #o.matrix_world = target_bone.matrix.inverted()
                    #o.parent = target_rig_obj
                    #o.parent_bone = target_bone.name
                    #o.matrix_world = o.matrix_world * o.matrix_parent_inverse.inverted()
                    #o.matrix_world = o.matrix_world * (target_bone.matrix_local * target_rig_obj.matrix_world).inverted()
                    #o.matrix_world = o.matrix_world * target_bone.matrix_local.inverted()
                    target_bone.select = False
                    #print(time.time() - start_time)

                #print(o.name)
                self.modify_shapekeys(o, target_key)
                    
                o.select = False

        #print(time.time() - start_time)
        #print()

        #print('Bolshet')
        #return {'FINISHED'}

        #print(context.object)

        # Deselect all again
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        #print('Bol foken shet')

        # Search for objects which use the source rig
        for o in objs:

            #if not o.type == 'MESH': continue

            #print(o.name)
            
            # Search for modifier using source rig
            modifier_found = None
            for mod in o.modifiers:
                if mod.type != 'ARMATURE': continue
                if mod.object == source_rig_obj:
                    modifier_found = mod
                    break

            if not modifier_found: continue

            scene.objects.active = o
            o.select = True

            if to_metarig:
                # Convert rigify vertex group to metarig
                for vg in o.vertex_groups:
                    key = [key for key, value in def_names.items() if value == vg.name]
                    if key: 
                        vg.name = key[0]
            else:
                # Convert metarig to rigify weight paint
                for vg in o.vertex_groups:
                    if vg.name in def_names:
                        vg.name = def_names[vg.name]

            # Change modifier object to target rig
            modifier_found.object = target_rig_obj

            self.modify_shapekeys(o, target_key)

            o.select = False

        # Revert state
        revert()

        # Layers change
        if to_metarig:
            for i, layer_active in enumerate(self.rigify_obj.layers):
                if layer_active:
                    scene.layers[i] = False
            for i, layer_active in enumerate(self.metarig_obj.layers):
                if layer_active:
                    scene.layers[i] = True
        else:
            for i, layer_active in enumerate(self.metarig_obj.layers):
                if layer_active:
                    scene.layers[i] = False
            for i, layer_active in enumerate(self.rigify_obj.layers):
                if layer_active:
                    scene.layers[i] = True

        #print(self.to_metarig)
        return {'FINISHED'}

class FastSelect(bpy.types.Operator):
    bl_idname = "object.rigify_fast_select"
    bl_label = "Select rigify bone faster"
    bl_description = "Select rigify bone faster"
    bl_options = {'REGISTER', 'UNDO'}

    type = EnumProperty(
        name = "Type",
        items=(
            ('ALL_IKS', "All IKs", ""),
            ('ALL_IKS_AND_TORSO', "All IKs and TORSO", ""),
            ('HAND_IKS', "Hand IKs", ""),
            ('HAND_IKS_AND_TORSO', "Hand IKs and Torso", ""),
            ('FEET_IKS', "Feet IKs", "")
            ), 
        default='ALL_IKS_AND_TORSO',
        )

    @classmethod
    def poll(cls, context):
        props = context.scene.basemesh_tools_props
        return props.rigify_object

    def execute(self, context):
        scene = context.scene
        props = scene.basemesh_tools_props

        rigify_object = scene.objects.get(props.rigify_object)

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        scene.objects.active = rigify_object
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='DESELECT')

        for bone in rigify_object.data.bones:
            if ((self.type == 'ALL_IKS_AND_TORSO' and bone.name in {'hand.ik.L', 'hand.ik.R', 'foot.ik.L', 'foot.ik.R', 'torso'}) or
                (self.type == 'HAND_IKS_AND_TORSO' and bone.name in {'hand.ik.L', 'hand.ik.R', 'torso'}) or
                (self.type == 'ALL_IKS' and bone.name in {'hand.ik.L', 'hand.ik.R', 'foot.ik.L', 'foot.ik.R'}) or
                (self.type == 'HAND_IKS' and bone.name in {'hand.ik.L', 'hand.ik.R'}) or
                (self.type == 'FEET_IKS' and bone.name in {'foot.ik.L', 'foot.ik.R'})
                ):
                bone.select = True

        return {'FINISHED'}

class SubPanelToggle(bpy.types.Operator):
    bl_idname = "view3d.basemesh_tools_subpanel_toggle"
    bl_label = "Toggle basemesh tools subpanel"
    bl_description = "Toggle basemesh tools subpanel"

    prop_name = StringProperty(default='')

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    def execute(self, context):
        props = context.scene.basemesh_tools_props

        if not hasattr(props, self.prop_name):
            return {'CANCELLED'}

        setattr(props, self.prop_name, not getattr(props, self.prop_name))

        return {'FINISHED'}

class BasemeshToolsPanel(bpy.types.Panel):
    #bl_category = "Basemesh"
    #bl_region_type = "TOOLS"
    bl_label = "Basemesh Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = 'UI'
    bl_options = {'DEFAULT_CLOSED'} 
    bl_context = "scene"

    def draw(self, context):
        scene = context.scene
        props = scene.basemesh_tools_props

        layout = self.layout
        c = layout.column(align=True)

        c.operator('mesh.toggle_metarig_rigify', icon='POSE_DATA')
        c.operator('mesh.apply_metarig_transform', icon='ARMATURE_DATA')

        c.separator()

        row = c.row(align=True)
        icon = 'TRIA_DOWN' if props.armature_object_settings_visible else 'TRIA_RIGHT'
        row.operator('view3d.basemesh_tools_subpanel_toggle', icon=icon , text='', emboss=False).prop_name = 'armature_object_settings_visible'
        row.label('Armature Object')

        if props.armature_object_settings_visible:
            box = c.box()
            inbox = box.column(align=True)
            inbox.prop_search(props, "metarig_object", bpy.data, "objects", text='Metarig', icon='OBJECT_DATA')
            inbox.prop_search(props, "rigify_object", bpy.data, "objects", text='Rigify', icon='OBJECT_DATA')

            metarig_object = scene.objects.get(props.metarig_object)
            rigify_object = scene.objects.get(props.rigify_object)

            if metarig_object and metarig_object.type == 'ARMATURE':
                inbox.prop(metarig_object, 'layers', text='Metarig Object Layers')

            if rigify_object and rigify_object.type == 'ARMATURE':
                inbox.prop(rigify_object, 'layers', text='Rigify Object Layers')

        row = c.row(align=True)
        icon = 'TRIA_DOWN' if props.shape_keys_settings_visible else 'TRIA_RIGHT'
        row.operator('view3d.basemesh_tools_subpanel_toggle', icon=icon , text='', emboss=False).prop_name = 'shape_keys_settings_visible'
        row.label('Shape Keys')

        if props.shape_keys_settings_visible:
            box = c.box()
            inbox = box.column(align=True)
            inbox.prop(props, 'metarig_shape_key_name', text='Metarig', icon='SHAPEKEY_DATA')
            inbox.prop(props, 'rigify_shape_key_name', text='Rigify', icon='SHAPEKEY_DATA')

        row = c.row(align=True)
        icon = 'TRIA_DOWN' if props.fast_select_settings_visible else 'TRIA_RIGHT'
        row.operator('view3d.basemesh_tools_subpanel_toggle', icon=icon , text='', emboss=False).prop_name = 'fast_select_settings_visible'
        row.label('Fast Select')

        if props.fast_select_settings_visible:
            c.operator('object.rigify_fast_select', text='All IKs and Torso', icon='GROUP_BONE').type = 'ALL_IKS_AND_TORSO'
            c.operator('object.rigify_fast_select', text='Hand IKs and Torso', icon='GROUP_BONE').type = 'HAND_IKS_AND_TORSO'
            c.operator('object.rigify_fast_select', text='All IKs', icon='GROUP_BONE').type = 'ALL_IKS'
            c.operator('object.rigify_fast_select', text='Hand IKs', icon='GROUP_BONE').type = 'HAND_IKS'
            c.operator('object.rigify_fast_select', text='Feet IKs', icon='GROUP_BONE').type = 'FEET_IKS'

class ForceMirrorPanel(bpy.types.Panel):
    #bl_category = "Basemesh"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Mirror Tools"
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'} 

    def draw(self, context):
        #scene = context.scene
        #props = scene.basemesh_tools_props

        layout = self.layout
        c = layout.column(align=True)

        #c.label('Flip Mirror Modifier:')
        c.operator('mesh.flip_mirror_modifier', icon='MOD_MIRROR')

        c.label('Force Mirror:')

        c.operator('mesh.force_mirror', text="X+ to X-", icon='MOD_MIRROR').mode = 'X_PLUS_MIN'
        c.operator('mesh.force_mirror', text="X- to X+", icon='MOD_MIRROR').mode = 'X_MIN_PLUS'
        c.operator('mesh.force_mirror', text="Y+ to Y-", icon='MOD_MIRROR').mode = 'Y_PLUS_MIN'
        c.operator('mesh.force_mirror', text="Y- to Y+", icon='MOD_MIRROR').mode = 'Y_MIN_PLUS'
        c.operator('mesh.force_mirror', text="Z+ to Z-", icon='MOD_MIRROR').mode = 'Z_PLUS_MIN'
        c.operator('mesh.force_mirror', text="Z- to Z+", icon='MOD_MIRROR').mode = 'Z_MIN_PLUS'
        c.operator('mesh.force_mirror_advance', text="Advance", icon='MOD_MIRROR')

class ShapeKeyMirrorPanel(bpy.types.Panel):
    #bl_category = "Basemesh"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_label = "Shape Key Edit"
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'} 

    def draw(self, context):
        #scene = context.scene
        #props = scene.basemesh_tools_props

        layout = self.layout
        c = layout.column(align=True)

        c.operator('mesh.shape_key_mirror', text="Mirror", icon='SHAPEKEY_DATA')
        c.operator('mesh.shape_key_reset', text="Reset", icon='SHAPEKEY_DATA')

def set_keybind():
    wm = bpy.context.window_manager

    q_keybind_found = False

    # Get object non modal keymaps
    km = wm.keyconfigs.addon.keymaps.get('Object Non-modal')
    if not km:
        km = wm.keyconfigs.addon.keymaps.new('Object Non-modal')
    
    # Search for Q keybind
    for kmi in km.keymap_items:
        
        if kmi.type == 'Q' and kmi.shift:
            if kmi.idname == 'mesh.toggle_metarig_rigify':
                q_keybind_found = True
                kmi.active = True
            else:
                # Deactivate other Q keybind
                kmi.active = False

    # Set Q Keybind
    if not q_keybind_found:
        new_shortcut = km.keymap_items.new('mesh.toggle_metarig_rigify', 'Q', 'PRESS', shift=True)

class BasemeshToolsProps(bpy.types.PropertyGroup):
    metarig_object = StringProperty(name='Metarig Object', default='')
    rigify_object = StringProperty(name='Rigify Object', default='')
    metarig_shape_key_name = StringProperty(name='Metarig Shape Key', default='Basis')
    rigify_shape_key_name = StringProperty(name='Rigify Shape Key', default='')

    # For collapse sections
    armature_object_settings_visible = BoolProperty(default=False)
    shape_keys_settings_visible = BoolProperty(default=False)
    fast_select_settings_visible = BoolProperty(default=False)

def register():
    bpy.utils.register_module(__name__)
    bpy.types.Scene.basemesh_tools_props = PointerProperty(type=BasemeshToolsProps)
    set_keybind()

def unregister():
	bpy.utils.unregister_module(__name__)

if __name__ == "__main__":
    register()
