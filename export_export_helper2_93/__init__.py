bl_info = {
	"name": "Export Helper",
	"author": "Kenetics",
	"version": (0, 1),
	"blender": (2, 93, 0),
	"location": "Properties > Scene > Export Helper Panel",
	"description": "Allows mesh export settings to be saved with blend file",
	"warning": "",
	"wiki_url": "",
	"category": "Import/Export"
}

import bpy
from bpy.props import EnumProperty, IntProperty, FloatVectorProperty, BoolProperty, FloatProperty, StringProperty
from bpy.types import PropertyGroup, UIList, Operator, Panel, AddonPreferences

"""
TODO
Add OBJ, other types
Add batching?
"""

"""
General Notes to Self
list(scene.somethingbig) - To see arrays in console

##Props
options = {
	"HIDDEN", # Hidden from UI, good for operators
	"SKIP_SAVE", # This prop is not saved in presets
	"ANIMATABLE",
	"LIBRARY_EDITABLE", # This prop can edited from linked instances (changes not saved)
	"PROPORTIONAL", # 
	"TEXTEDIT_UPDATE"
	ENUM_FLAG - Property is an EnumProperty and multiple entries can be selected (Shift+LMB)
}

#Number
min, max, soft_min, soft_max
unit = "LENGTH", "AREA", "VOLUME", "ROTATION", "TIME", "VELOCITY", "ACCELERATION", "MASS", "CAMERA", "POWER"
subtype = "PIXEL", "UNSIGNED", "PERCENTAGE", "FACTOR", "ANGLE", "TIME", "DISTANCE", "DISTANCE_CAMERA"
"POWER", "TEMPERATURE"

#Float
precision = 3 # display precision
subtype = ""

#XVector
size = 3
subtype = "COLOR" , "TRANSLATION", "DIRECTION", "VELOCITY", "ACCELERATION", "MATRIX", "EULER"
"QUATERNION", "AXISANGLE", "XYZ", "XYZ_LENGTH", "COLOR_GAMMA", "COORDINATES", "LAYER"
"LAYER_MEMBER"

#String
subtype = "DIR_PATH", "FILE_PATH", "FILE_NAME", "BYTE_STRING", "PASSWORD"

#Enum
Dynamic
def get_enum_items(self, context):
	enum_list = []
	
	for obj in context.selected_objects:
		enum_list.append( (obj.name, obj.name, "") )
	
	return enum_list
obj_name : EnumProperty(items=get_enum_items, name="Object Name")
Static
obj_name : EnumProperty(
	items=[
		("ITEM","Item Name", "Item Description", "UI_ICON", 0),
		("ITEM2","Item Name2", "Item Description", "UI_ICON", 1)
	],
	name="Object Name",
	description=""
)

##Collections
context.scene.collection - Master Scene collection
context.collection - Active Collection
collection.all_objects - all objects in this and child collections
collection.objects - objects in this collection
collection.children - child collections
collection.children.link(collection2) - link collection2 as child of collection
	will throw error if already in collection
collection.children.unlink(collection2) - unlink collection2 as child of collection
collection.objects.link(obj) - link object to collection
collection.objects.unlink(obj) - unlink object

##Window
context.area.type - Type of area

Window Manager
context.window_manager

"""

## Helper Functions
def get_addon_preferences():
	return bpy.context.preferences.addons[__package__].preferences

def get_fbx_settings(context):
	return context.scene.eh_fbx_settings

def correct_fbx_end(self, context):
	# self["filepath"][self["filepath"].rfind("."):] returns string from last dot to end of string
	if self["filepath"][self["filepath"].rfind("."):] != ".fbx":
		self["filepath"] = self["filepath"] + ".fbx"

# TODO: make export settings struct
## Structs
"""
bpy.ops.export_scene.fbx(
	filepath="", 
	check_existing=True,
	filter_glob="*.fbx",
Write a FBX file
"""

class EH_FBXExportSettings(PropertyGroup):
	filepath : StringProperty(name = "File Path", description="Filepath used for exporting the file", subtype="FILE_PATH", update=correct_fbx_end)
	check_existing : BoolProperty(name="Check Existing",description="Check and warn on overwriting existing files", default=True)
	#filter_glob
	use_selection : BoolProperty(name="Selected Objects",description="Export selected and visible objects only", default=False)
	use_active_collection : BoolProperty(name="Active Collection",description="Export only objects from the active collection (and its children)", default=False)
	global_scale : FloatProperty(name="Scale", description="Scale all data (Some importers do not support scaled armatures!)", default=1.0,min=0.001,max=1000)
	apply_unit_scale : BoolProperty(name="Apply Unit", description="Take into account current Blender units settings (if unset, raw Blender Units values are used as-is)",default=True)
	apply_scale_options : EnumProperty(name="Apply Scalings",description="",items=[
		("FBX_SCALE_NONE", "All Local", "Apply custom scaling and units scaling to each object transformation, FBX scale remains at 1.0."),
		("FBX_SCALE_UNITS", "FBX Units Scale", "Apply custom scaling to each object transformation, and units scaling to FBX scale."),
		("FBX_SCALE_CUSTOM", "FBX Custom Scale", "Apply custom scaling to FBX scale, and units scaling to each object transformation."),
		("FBX_SCALE_ALL", "FBX All", "Apply custom scaling and units scaling to FBX scale."),
	])
	use_space_transform : BoolProperty(name="Use Space Transform",description="Apply global space transform to the object rotations. When disabled only the axis space is written to the file and all object transforms are left as-is",default=True)
	bake_space_transform : BoolProperty(name="Apply Transform",description="Bake space transform into object data, avoids getting unwanted rotations to objects when target space is not aligned with Blender’s space (WARNING! experimental option, use at own risks, known broken with armatures/animations)",default=False)
	object_types : EnumProperty(name="Object Types",description="Which kind of object to export",options={"ENUM_FLAG"},items=[
		('EMPTY', "Empty", ""),
		('CAMERA', "Camera", ""),
		('LIGHT', "Lamp", ""),
		('ARMATURE', "Armature", "WARNING: not supported in dupli/group instances."),
		('MESH', "Mesh", ""),
		('OTHER', "Other", "Other geometry types, like curve, metaball, etc. (converted to meshes)"),
	])
	use_mesh_modifiers : BoolProperty(name="Apply Modifiers",description="Apply modifiers to mesh objects (except Armature ones) - WARNING: prevents exporting shape keys",default=True)
	#use_mesh_modifiers_render : BoolProperty(name="Use Modifiers Render Setting",description="",default=True)
	mesh_smooth_type : EnumProperty(name="Smoothing",description="Export smoothing information (prefer ‘Normals Only’ option if your target importer understand split normals)",items=[
		('OFF',"Normals Only","Export only normals instead of writing edge or face smoothing data."),
		('FACE',"Face","Write face smoothing"),
		('EDGE',"Edge","Write edge smoothing"),
	])
	use_subsurf : BoolProperty(name="Export Subdivision Surface",description="Export the last Catmull-Rom subdivision modifier as FBX subdivision (does not apply the modifier even if ‘Apply Modifiers’ is enabled)",default=False)
	use_mesh_edges : BoolProperty(name="Loose Edges",description="Export loose edges (as two-vertices polygons)",default=False)
	use_tspace : BoolProperty(name="Tangent Space",description="Add binormal and tangent vectors, together with normal they form the tangent space (will only work correctly with tris/quads only meshes!)",default=False)
	use_custom_props : BoolProperty(name="Custom Properties",description="Export custom properties",default=False)
	add_leaf_bones : BoolProperty(name="Add Leaf Bones",description="Append a final bone to the end of each chain to specify last bone length (use this when you intend to edit the armature from exported data)",default=True)
	primary_bone_axis : EnumProperty(name="Primary Bone Axis",description="",default="Y",items=[
		('X',"X",""),
		('Y', "Y", ""),
		('Z',"Z",""),
		('-X',"-X",""),
		('-Y',"-Y",""),
		('-Z',"-Z",""),
	])
	secondary_bone_axis : EnumProperty(name="Secondary Bone Axis",description="",default="X",items=[
		('X',"X",""),
		('Y',"Y",""),
		('Z',"Z",""),
		('-X',"-X",""),
		('-Y',"-Y",""),
		('-Z',"-Z",""),
	])
	use_armature_deform_only : BoolProperty(name="Only Deform Bones",description="Only write deforming bones (and non-deforming ones when they have deforming children)",default=False)
	armature_nodetype : EnumProperty(name="Armature FBXNode Type",description="FBX type of node (object) used to represent Blender’s armatures (use Null one unless you experience issues with other app, other choices may no import back perfectly in Blender…)",items=[
		('NULL',"Null","‘Null’ FBX node, similar to Blender’s Empty (default)."),
		('ROOT',"Root","‘Root’ FBX node, supposed to be the root of chains of bones…."),
		('LIMBNODE',"LimbNode","‘LimbNode’ FBX node, a regular joint between two bones…."),
	])
	bake_anim : BoolProperty(name="Baked Animation",description="Export baked keyframe animation",default=True)
	bake_anim_use_all_bones : BoolProperty(name="Key All Bones",description="Force exporting at least one key of animation for all bones (needed with some target applications, like UE4)",default=True)
	bake_anim_use_nla_strips : BoolProperty(name="NLA Strips",description="Export each non-muted NLA strip as a separated FBX’s AnimStack, if any, instead of global scene animation",default=True)
	bake_anim_use_all_actions : BoolProperty(name="All Actions",description="Export each action as a separated FBX’s AnimStack, instead of global scene animation (note that animated objects will get all actions compatible with them, others will get no animation at all)",default=True)
	bake_anim_force_startend_keying : BoolProperty(name="Force Start/End Keying",description="Always add a keyframe at start and end of actions for animated channels",default=True)
	bake_anim_step : FloatProperty(name="Sampling Rate",description="How often to evaluate animated values (in frames)",default=1.0, min=0.01, max=100.0)
	bake_anim_simplify_factor : FloatProperty(name="Simplify",description="How much to simplify baked values (0.0 to disable, the higher the more simplified)",default=1.0, min=0.0, max=100.0)
	path_mode : EnumProperty(name="Path Mode",description="Method used to reference paths",items=[
		('AUTO',"Auto","Use Relative paths with subdirectories only"),
		('ABSOLUTE',"Absolute","Always write absolute paths"),
		('RELATIVE',"Relative","Always write relative paths (where possible)."),
		('MATCH',"Match","Match Absolute/Relative setting with input path."),
		('STRIP',"Strip Path","Filename only."),
		('COPY',"Copy","Copy the file to the destination path (or subdirectory)."),
	])
	embed_textures : BoolProperty(name="Embed Textures",description="Embed textures in FBX binary file (only for “Copy” path mode!)",default=False)
	batch_mode : EnumProperty(name="Batch Mode",description="",default="OFF",items=[
		('OFF',"Off","Active scene to file"),
		('SCENE',"Scene","Each scene as a file."),
		('COLLECTION',"Collection","Each collection (data-block ones) as a file, does not include content of children collections."),
		('SCENE_COLLECTION',"Scene Collections","Each collection (including master, non-data-block ones) of each scene as a file, including content from children collections."),
		('ACTIVE_SCENE_COLLECTION',"Active Scene Collections","Each collection (including master, non-data-block one) of the active scene as a file, including content from children collections."),
	])
	use_batch_own_dir : BoolProperty(name="Batch Own Dir",description="Create a dir for each exported file",default=True)
	use_metadata : BoolProperty(name="Use Metadata",description="",default=True)
	axis_forward : EnumProperty(name="Forward",description="",default="-Z",items=[
		('X',"X",""),
		('Y',"Y",""),
		('Z',"Z",""),
		('-X',"-X",""),
		('-Y',"-Y",""),
		('-Z',"-Z",""),
	])
	axis_up : EnumProperty(name="Up",description="",default="Y",items=[
		('X',"X",""),
		('Y',"Y",""),
		('Z',"Z",""),
		('-X',"-X",""),
		('-Y',"-Y",""),
		('-Z',"-Z",""),
	])
	
	def draw(self, context):
		layout = self.layout
		settings = context.scene.eh_fbx_settings
		
		## Top
		layout.prop(settings, "filepath")
		layout.use_property_split = True
		operator = layout.operator(EH_OT_fbx_export.bl_idname)
		row = layout.row(align=True)
		row.prop(settings, "path_mode")
		sub = row.row(align=True)
		sub.enabled = settings.path_mode == "COPY"
		sub.prop(settings, "embed_textures", text="", icon="PACKAGE" if settings.embed_textures else "UGLYPACKAGE")
		row = layout.row(align=True)
		row.prop(settings, "batch_mode")
		sub = row.row(align=True)
		sub.prop(settings, "use_batch_own_dir", text="", icon='NEWFOLDER')
		
		## Include
		layout.label(text="Include")
		box = layout.box()
		col = box.column(align=True)
		
		sublayout = col.column(heading="Limit to")
		sublayout.enabled = (settings.batch_mode == 'OFF')
		sublayout.prop(settings, "use_selection")
		sublayout.prop(settings, "use_active_collection")

		col.column().prop(settings, "object_types")
		col.prop(settings, "use_custom_props")

		## Transform
		layout.label(text="Transform")
		box = layout.box()
		col = box.column(align=True)

		col.prop(settings, "global_scale")
		col.prop(settings, "apply_scale_options")

		col.prop(settings, "axis_forward")
		col.prop(settings, "axis_up")

		col.prop(settings, "apply_unit_scale")
		col.prop(settings, "use_space_transform")
		row = col.row()
		row.prop(settings, "bake_space_transform")
		row.label(text="", icon='ERROR')
		
		## Geometry
		layout.label(text="Geometry")
		box = layout.box()
		col = box.column(align=True)

		col.prop(settings, "mesh_smooth_type")
		col.prop(settings, "use_subsurf")
		col.prop(settings, "use_mesh_modifiers")
		col.prop(settings, "use_mesh_edges")
		sub = col.row()
		sub.prop(settings, "use_tspace")

		## Armature
		layout.label(text="Armature")
		box = layout.box()
		col = box.column(align=True)

		col.prop(settings, "primary_bone_axis")
		col.prop(settings, "secondary_bone_axis")
		col.prop(settings, "armature_nodetype")
		col.prop(settings, "use_armature_deform_only")
		col.prop(settings, "add_leaf_bones")

		layout.use_property_split = False
		layout.prop(settings, "bake_anim")
		layout.use_property_split = True
		box = layout.box()
		col = box.column(align=True)
		col.enabled = settings.bake_anim
		col.prop(settings, "bake_anim_use_all_bones")
		col.prop(settings, "bake_anim_use_nla_strips")
		col.prop(settings, "bake_anim_use_all_actions")
		col.prop(settings, "bake_anim_force_startend_keying")
		col.prop(settings, "bake_anim_step")
		col.prop(settings, "bake_anim_simplify_factor")


## Operators
# Adding operator that calls other op with params because if add operator button to layout and add params to that, depsgraph changed keeps getting called as long as button is viewed
class EH_OT_fbx_export(Operator):
	"""Exports FBX with settings from Scene"""
	bl_idname = "eh.fbx_export"
	bl_label = "EH FBX Export"
	bl_options = {'REGISTER'}

	@classmethod
	def poll(cls, context):
		return True

	def execute(self, context):
		settings = get_fbx_settings(context)
		bpy.ops.export_scene.fbx(
			filepath = settings.filepath,
			path_mode = settings.path_mode,
			embed_textures = settings.embed_textures,
			batch_mode = settings.batch_mode,
			use_batch_own_dir = settings.use_batch_own_dir,
			use_selection = settings.use_selection,
			use_active_collection = settings.use_active_collection,
			global_scale = settings.global_scale,
			apply_scale_options = settings.apply_scale_options,
			axis_forward = settings.axis_forward,
			axis_up = settings.axis_up,
			apply_unit_scale = settings.apply_unit_scale,
			use_space_transform = settings.use_space_transform,
			mesh_smooth_type = settings.mesh_smooth_type,
			use_subsurf = settings.use_subsurf,
			use_mesh_modifiers = settings.use_mesh_modifiers,
			use_mesh_edges = settings.use_mesh_edges,
			use_tspace = settings.use_tspace,
			primary_bone_axis = settings.primary_bone_axis,
			secondary_bone_axis = settings.secondary_bone_axis,
			armature_nodetype = settings.armature_nodetype,
			use_armature_deform_only = settings.use_armature_deform_only,
			add_leaf_bones = settings.add_leaf_bones,
			bake_anim = settings.bake_anim,
			bake_anim_use_all_bones = settings.bake_anim_use_all_bones,
			bake_anim_use_nla_strips = settings.bake_anim_use_nla_strips,
			bake_anim_use_all_actions = settings.bake_anim_use_all_actions,
			bake_anim_force_startend_keying = settings.bake_anim_force_startend_keying,
			bake_anim_step = settings.bake_anim_step,
			bake_anim_simplify_factor = settings.bake_anim_simplify_factor
		)
		return {'FINISHED'}


## UI
class EH_PT_fbx_export_helper_panel(Panel):
	bl_label = "FBX Export Helper Panel"
	bl_idname = "EH_PT_fbx_export_helper"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = "scene"
	#object, objectmode, mesh_edit, curve_edit, render, output

	def draw(self, context):
		#layout = self.layout
		# layout.use_property_split = True
		
		#op = layout.operator("export_scene.fbx")
		EH_FBXExportSettings.draw(self, context)
		

## Append to UI Helper Functions
# to get menu class name, hover over menu in Blender. Name is like VIEW3D_MT_add
# menus are listed in bpy.types
#def draw_func(self, context):
#	layout = self.layout
#


## Preferences
class EH_addon_preferences(AddonPreferences):
	bl_idname = __package__
	
	# Properties
	show_mini_manual : BoolProperty(name="Show Mini Manual", default=False)

	def draw(self, context):
		layout = self.layout
		
		layout.prop(self, "show_mini_manual", toggle=True)
		
		if self.show_mini_manual:
			layout.label(text="Topic", icon="DOT")
			layout.label(text="Details",icon="THREE_DOTS")


## Register
classes = (
	EH_FBXExportSettings,
	EH_PT_fbx_export_helper_panel,
	EH_OT_fbx_export
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	
	## Add Custom Properties
	#bpy.Types.WindowManager.something = IntProperty() # to not save things with blend file
	bpy.types.Scene.eh_fbx_settings = bpy.props.PointerProperty(type=EH_FBXExportSettings)
	
	## Append to UI
	# bpy.types.CLASS.append(helper_func)

def unregister():
	## Remove from UI
	# bpy.types.CLASS.remove(helper_func)
	
	## Remove Custom Properties
	del bpy.types.Scene.eh_fbx_settings
	#del bpy.Types.WindowManager.something
	
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)

if __name__ == "__main__":
	register()
