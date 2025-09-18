# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from . import recording
from . import nodegroups
from . import ui
from . import custom_inputs

classes = (
    recording.CLE_OT_LiveControllerInputs,
    recording.CLE_OT_RecordControllerInputs,
    nodegroups.CLE_OT_CreateNodegroup,
    ui.CLE_PT_Main,
    custom_inputs.CLE_CustomInput,
    custom_inputs.CLE_OT_AddCustomInput,
    custom_inputs.CLE_OT_EditCustomInput,
    custom_inputs.CLE_OT_SetMappedInput,
    custom_inputs.CLE_OT_RemoveCustomInput,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # Scene properties for modal states
    bpy.types.Scene.cle_record_modal_running = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.cle_live_modal_running = bpy.props.BoolProperty(default=False)
    
    # Recording properties
    bpy.types.Scene.cle_record_rate = bpy.props.IntProperty(
        name="Record Rate",
        description="Rate at which inputs are recorded (Hz)",
        default=60,
        min=1,
        max=120
    )
    bpy.types.Scene.cle_record_auto_keyframe = bpy.props.BoolProperty(
        name="Auto Keyframe",
        description="Automatically create keyframes during recording",
        default=True
    )
    
    # Camera controller properties
    bpy.types.Scene.cle_camera_controller_enabled = bpy.props.BoolProperty(
        name="Camera Controller Enabled",
        description="Enable camera controller functionality",
        default=False
    )
    bpy.types.Scene.cle_camera_object = bpy.props.PointerProperty(
        name="Camera Object",
        description="Camera object to control",
        type=bpy.types.Object,
        poll=lambda self, obj: obj.type == 'CAMERA'
    )
    bpy.types.Scene.cle_target_object = bpy.props.PointerProperty(
        name="Target Object",
        description="Target object for camera to look at (optional)",
        type=bpy.types.Object
    )
    bpy.types.Scene.cle_camera_sensitivity = bpy.props.FloatProperty(
        name="Camera Sensitivity",
        description="Sensitivity of camera movement",
        default=1.0,
        min=0.1,
        max=10.0,
        step=0.1
    )
    bpy.types.Scene.cle_camera_smoothing = bpy.props.FloatProperty(
        name="Camera Smoothing",
        description="Smoothing factor for camera movement",
        default=0.1,
        min=0.0,
        max=1.0,
        step=0.01
    )
    
    # Custom inputs collection
    bpy.types.Scene.cle_custom_inputs = bpy.props.CollectionProperty(
        name="Custom Inputs",
        description="Collection of custom controller input mappings",
        type=custom_inputs.CLE_CustomInput
    )
    

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
