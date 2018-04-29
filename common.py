import bpy

mirror_dict = {
        'left' : 'right',
        'Left' : 'Right',
        '.L' : '.R',
        '_L' : '_R',
        '.l' : '.r',
        '_l' : '_r'
        }

def in_active_layers(obj):
    sce = bpy.context.scene
    return any([l for i, l in enumerate(obj.layers) if l and sce.layers[i]])

def get_mirror_name(name):

    # Split name for detect digit at the end
    splitnames = name.split('.')
    last_word = splitnames[-1]

    # If last word is digit, crop it
    extra = ''
    crop_name = name
    if last_word.isdigit() and len(splitnames) > 1:
        extra = '.' + last_word
        crop_name = name[:-len(last_word)-1]

    mir_name = ''
    for l, r in mirror_dict.items():

        if crop_name.endswith(l):
            ori = l
            mir = r
        elif crop_name.endswith(r):
            ori = r
            mir = l
        else:
            continue

        mir_name = crop_name[:-len(ori)] + mir + extra
        break

    return mir_name

class ObjectState:
    def __init__(self, obj):
        self.obj = obj
        self.active_shape_key_index = obj.active_shape_key_index

    def revert(self):
        self.obj.active_shape_key_index = self.active_shape_key_index

class MeshState:
    def __init__(self, mesh):
        self.mesh = mesh

        # Remember shape keys
        self.shape_keys_values = {}
        if mesh.shape_keys:
            for kb in mesh.shape_keys.key_blocks:
                self.shape_keys_values[kb.name] = kb.value

    def revert(self):
        # Reveert shape keys
        if self.mesh.shape_keys:
            for name, value in self.shape_keys_values.items():
                kb = self.mesh.shape_keys.key_blocks.get(name)
                if kb: kb.value = value
