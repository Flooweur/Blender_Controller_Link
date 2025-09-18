import bpy
from . import controller
from . import recording

class CLE_PT_Main(bpy.types.Panel):
    """
    Main UI panel for Controller Link Extended addon.
    
    This panel provides the primary user interface for the addon, displayed
    in the 3D Viewport's sidebar under the "CL Extended" tab. It includes:
    - Start/stop buttons for live and recording modes
    - Controller connection status display
    - Real-time display of all controller inputs (axes and buttons)
    
    The panel dynamically updates its content based on the current state:
    - Shows different buttons when modes are active/inactive
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

        # LIVE INPUT BUTTON - Main control for real-time input
        row = layout.row()
        row.scale_y = 1.5  # Make button larger for easier clicking
        
        # Only show live button when recording isn't active
        if not scene.cle_record_modal_running:
            if scene.cle_live_modal_running:
                # Live mode is active - show stop button
                row.operator("wm.cle_live_controller_inputs", text="Stop", icon='PAUSE')
            else:
                # Live mode is inactive - show start button
                row.operator("wm.cle_live_controller_inputs", text="Get Controller Inputs", icon='PLAY')

        # Show additional controls only when a mode is active
        if scene.cle_live_modal_running or scene.cle_record_modal_running:

            # RECORD BUTTON - Available when live mode is running
            row = layout.row()
            row.scale_y = 1.5  # Make button larger for easier clicking
            if scene.cle_record_modal_running:
                # Recording is active - show stop recording button
                row.operator("wm.cle_record_controller_inputs", text="Stop Recording", icon='PAUSE')
            else:
                # Recording is inactive but live mode is running - show record button
                row.operator("wm.cle_record_controller_inputs", text="Record", icon='REC')

            layout.separator()  # Visual separator between buttons and info

            # Get the active controller handler for status display
            handler = None
            if scene.cle_live_modal_running:
                # Get controller from live mode operator
                handler = getattr(recording.CLE_OT_LiveControllerInputs, "_controller", None)
            elif scene.cle_record_modal_running:
                # Get controller from recording mode operator
                handler = getattr(recording.CLE_OT_RecordControllerInputs, "_controller", None)

            # Display controller connection status
            if handler and handler.is_connected():
                # Show connected controller name
                layout.label(text=f"Controller: {handler.controller_name}")
            else:
                # Show disconnected state
                layout.label(text="No controller detected.")

            # Get the object that stores controller data
            cle_reader = controller.get_reader()
            if not cle_reader:
                layout.label(text="No reader object found.")
                return  # Can't show input values without reader object

            # AXES SECTION - Display all analog stick and trigger values
            layout.label(text="Axes:")  # Section header
            # Get all axis properties and sort them for consistent display
            axis_keys = sorted(k for k in cle_reader.keys() if k.startswith("controller_axis_"))
            for prop_name in axis_keys:
                row = layout.row()
                # Display axis with cleaned-up name (remove "controller_axis_" prefix)
                display_name = prop_name.replace("controller_axis_", "").capitalize()
                row.prop(cle_reader, f'["{prop_name}"]', text=display_name)

            layout.separator()  # Visual separator between sections

            # BUTTONS SECTION - Display all button states
            layout.label(text="Buttons:")  # Section header
            # Get all button properties and sort them for consistent display
            button_keys = sorted(k for k in cle_reader.keys() if k.startswith("controller_button_"))
            for prop_name in button_keys:
                row = layout.row()
                # Display button with cleaned-up name (remove "controller_button_" prefix)
                display_name = prop_name.replace("controller_button_", "").capitalize()
                row.prop(cle_reader, f'["{prop_name}"]', text=display_name)
