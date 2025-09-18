import bpy
from . import controller
from . import recording

class CLE_PT_Main(bpy.types.Panel):
    """
    Main UI panel for Controller Link Extended addon.
    
    This panel provides the primary user interface for the addon, displayed
    in the 3D Viewport's sidebar under the "CL Extended" tab. It includes:
    - Get Controller Inputs button (initial state)
    - Stop button when controller is connected
    - Record section with rate controls
    - Camera Controller section with camera/target selection
    - Custom Inputs section with + button for adding custom inputs
    
    The panel dynamically updates its content based on the current state:
    - Shows different sections when controller is connected
    - Displays controller information when connected
    - Shows live input values during operation
    """
    bl_label = "Controller Link Extended"
    bl_idname = "CLE_PT_Main"
    bl_space_type = 'VIEW_3D'    # Display in 3D Viewport
    bl_region_type = 'UI'        # In the sidebar (N-panel)
    bl_category = "CL Extended"  # Tab name in sidebar

    def draw(self, context):
        """
        Draw the panel UI elements.
        
        This method is called by Blender to render the panel contents.
        It dynamically adjusts the interface based on the current state
        of the addon (live mode, recording mode, or inactive).
        
        Args:
            context: Blender context containing scene and other data
        """
        layout = self.layout
        scene = context.scene

        # Check if controller is connected
        controller_connected = scene.cle_live_modal_running or scene.cle_record_modal_running
        
        if not controller_connected:
            # Initial state - only show Get Controller Inputs button
            row = layout.row()
            row.scale_y = 1.5
            row.operator("wm.cle_live_controller_inputs", text="Get Controller Inputs", icon='PLAY')
        else:
            # Controller is connected - show all sections
            
            # STOP BUTTON - At the top
            row = layout.row()
            row.scale_y = 1.5
            if scene.cle_live_modal_running:
                row.operator("wm.cle_live_controller_inputs", text="Stop", icon='PAUSE')
            elif scene.cle_record_modal_running:
                row.operator("wm.cle_record_controller_inputs", text="Stop", icon='PAUSE')
            
            layout.separator()
            
            # RECORD SECTION
            box = layout.box()
            box.label(text="Record", icon='REC')
            
            # Record button
            row = box.row()
            row.scale_y = 1.2
            if scene.cle_record_modal_running:
                row.operator("wm.cle_record_controller_inputs", text="Stop Recording", icon='PAUSE')
            else:
                row.operator("wm.cle_record_controller_inputs", text="Record", icon='REC')
            
            # Recording rate input
            row = box.row()
            row.prop(scene, "cle_record_rate", text="Rate (Hz)")
            
            # Additional recording options
            row = box.row()
            row.prop(scene, "cle_record_auto_keyframe", text="Auto Keyframe")
            
            layout.separator()
            
            # CAMERA CONTROLLER SECTION
            box = layout.box()
            
            # Section header with enable checkbox
            row = box.row()
            row.prop(scene, "cle_camera_controller_enabled", text="Camera Controller")
            
            # Enable/disable the section based on checkbox
            if scene.cle_camera_controller_enabled:
                # Camera selection
                row = box.row()
                row.prop(scene, "cle_camera_object", text="Camera")
                
                # Target selection
                row = box.row()
                row.prop(scene, "cle_target_object", text="Target")
                
                # Camera control options
                row = box.row()
                row.prop(scene, "cle_camera_sensitivity", text="Sensitivity")
                
                row = box.row()
                row.prop(scene, "cle_camera_smoothing", text="Smoothing")
                
                # Camera mode info
                if scene.cle_target_object:
                    box.label(text="Mode: Look At Target", icon='VIEW_CAMERA')
                else:
                    box.label(text="Mode: Free Camera", icon='CAMERA_DATA')
            else:
                # Greyed out state
                box.enabled = False
                box.label(text="Camera Controller Disabled")
            
            layout.separator()
            
            # CUSTOM INPUTS SECTION
            box = layout.box()
            box.label(text="Custom Inputs", icon='SETTINGS')
            
            # Show existing custom inputs
            custom_inputs = getattr(scene, 'cle_custom_inputs', [])
            if custom_inputs:
                for i, custom_input in enumerate(custom_inputs):
                    row = box.row()
                    row.label(text=custom_input.name)
                    op = row.operator("wm.cle_edit_custom_input", text="", icon='EDIT')
                    op.index = i
                    op = row.operator("wm.cle_remove_custom_input", text="", icon='X')
                    op.index = i
            else:
                box.label(text="No custom inputs")
            
            # Add new custom input button
            row = box.row()
            row.scale_y = 1.2
            row.operator("wm.cle_add_custom_input", text="+ Add Custom Input", icon='ADD')
            
            layout.separator()
            
            # CONTROLLER STATUS
            box = layout.box()
            box.label(text="Controller Status", icon='INFO')
            
            # Get the active controller handler for status display
            handler = None
            if scene.cle_live_modal_running:
                handler = getattr(recording.CLE_OT_LiveControllerInputs, "_controller", None)
            elif scene.cle_record_modal_running:
                handler = getattr(recording.CLE_OT_RecordControllerInputs, "_controller", None)

            if handler and handler.is_connected():
                box.label(text=f"Connected: {handler.controller_name}")
            else:
                box.label(text="No controller detected.")

            # Show live input values if available
            cle_reader = controller.get_reader()
            if cle_reader:
                # AXES SECTION - Display all analog stick and trigger values
                box = layout.box()
                box.label(text="Axes", icon='IPO_EASE_IN_OUT')
                axis_keys = sorted(k for k in cle_reader.keys() if k.startswith("controller_axis_"))
                for prop_name in axis_keys:
                    row = box.row()
                    display_name = prop_name.replace("controller_axis_", "").capitalize()
                    row.prop(cle_reader, f'["{prop_name}"]', text=display_name)

                # BUTTONS SECTION - Display all button states
                box = layout.box()
                box.label(text="Buttons", icon='RADIOBUT_ON')
                button_keys = sorted(k for k in cle_reader.keys() if k.startswith("controller_button_"))
                for prop_name in button_keys:
                    row = box.row()
                    display_name = prop_name.replace("controller_button_", "").capitalize()
                    row.prop(cle_reader, f'["{prop_name}"]', text=display_name)
