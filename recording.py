"""
Recording and animation module for Blender Controller Link Extended.
Handles keyframing and recording operations with improved error handling.
"""

import bpy
import logging
from typing import Optional
from .controller import SDL2Controller, create_reader, get_reader

# Set up logging
logger = logging.getLogger(__name__)

def keyframe_inputs(scene: bpy.types.Scene) -> None:
    """
    Keyframe controller inputs for the current frame with error handling.
    
    Args:
        scene: Blender scene object
    """
    try:
        reader = get_reader()
        if not reader:
            logger.warning("No reader object found for keyframing")
            return

        frame = scene.frame_current
        keyframed_count = 0
        
        for prop_name, prop_value in reader.items():
            if prop_name.startswith("controller_"):
                try:
                    reader.keyframe_insert(data_path=f'["{prop_name}"]', frame=frame)
                    keyframed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to keyframe {prop_name}: {e}")
                    continue
        
        if keyframed_count > 0:
            logger.debug(f"Keyframed {keyframed_count} controller inputs at frame {frame}")
            
    except Exception as e:
        logger.error(f"Error in keyframe_inputs: {e}")

class CLE_OT_LiveControllerInputs(bpy.types.Operator):
    """
    Operator for live controller input capture without recording.
    
    This modal operator continuously polls controller inputs and updates
    the CLE_reader object properties in real-time. It's designed for:
    - Live performance and interaction
    - Testing controller mappings
    - Real-time animation driving
    
    The operator runs in modal mode with a 60Hz timer, providing smooth
    real-time input updates. It can be started and stopped via the UI.
    
    Class Attributes:
        _timer: Blender timer for modal updates
        _controller: SDL2Controller instance for input polling
    """
    bl_idname = "wm.cle_live_controller_inputs"
    bl_label = "Get Controller Inputs"
    bl_description = "Start/stop live controller input capture"

    _timer = None
    _controller: Optional[SDL2Controller] = None

    def modal(self, context, event):
        """
        Modal operator update loop for live controller input.
        
        Called by Blender's event system approximately 60 times per second
        while the operator is running. Handles controller polling and
        responds to user cancellation events.
        
        Args:
            context: Blender context
            event: Blender event (timer, keyboard, etc.)
            
        Returns:
            set: Blender operator return status
                - {'PASS_THROUGH'}: Continue modal operation
                - {'CANCELLED'}: Stop and cleanup
        """
        try:
            if event.type == 'TIMER':
                if self._controller and self._controller.is_connected():
                    reader = get_reader()
                    if reader:
                        success = self._controller.poll_inputs(reader)
                        if success:
                            # Trigger driver updates
                            reader.location = reader.location
                        else:
                            logger.warning("Failed to poll controller inputs")
                else:
                    logger.warning("Controller disconnected during live mode")
                    self.cancel(context)
                    return {'CANCELLED'}
            
            if not context.scene.cle_live_modal_running or event.type in {'ESC'}:
                self.cancel(context)
                return {'CANCELLED'}
                
            return {'PASS_THROUGH'}
            
        except Exception as e:
            logger.error(f"Error in live controller modal: {e}")
            self.cancel(context)
            return {'CANCELLED'}

    def execute(self, context):
        """
        Initialize and start the live controller input operator.
        
        Sets up the controller, creates necessary objects, configures the timer,
        and enters modal mode. This method is called when the user clicks the
        "Get Controller Inputs" button in the UI.
        
        Args:
            context: Blender context
            
        Returns:
            set: Blender operator return status
                - {'RUNNING_MODAL'}: Successfully started modal operation
                - {'CANCELLED'}: Failed to start, operation cancelled
        """
        try:
            # Create reader object
            reader = create_reader()
            if not reader:
                self.report({'ERROR'}, "Failed to create reader object")
                return {'CANCELLED'}

            # Stop recording mode if running
            if context.scene.cle_record_modal_running:
                context.scene.cle_record_modal_running = False

            # Toggle live mode
            if context.scene.cle_live_modal_running:
                context.scene.cle_live_modal_running = False
                return {'CANCELLED'}

            # Initialize controller
            try:
                self._controller = SDL2Controller()
                if not self._controller.is_connected():
                    self.report({'WARNING'}, "No controller detected")
                    # Continue anyway in case controller gets connected later
                    
            except Exception as e:
                logger.error(f"Failed to initialize controller: {e}")
                self.report({'ERROR'}, f"Controller initialization failed: {e}")
                return {'CANCELLED'}

            # Set up timer and modal
            wm = context.window_manager
            self._timer = wm.event_timer_add(time_step=1/60, window=context.window)
            wm.modal_handler_add(self)

            # Set flag
            context.scene.cle_live_modal_running = True

            # Create node group
            try:
                bpy.ops.wm.cle_create_nodegroup()
            except Exception as e:
                logger.warning(f"Failed to create node group: {e}")
                # Continue without node group

            self.report({'INFO'}, f"Started live controller inputs: {self._controller.controller_name if self._controller else 'No controller'}")
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            logger.error(f"Error starting live controller inputs: {e}")
            self.report({'ERROR'}, f"Failed to start live inputs: {e}")
            return {'CANCELLED'}

    def cancel(self, context):
        """
        Clean up and cancel the live controller input operator.
        
        Removes timers, cleans up controller resources, and resets UI state.
        This method is called when the user stops the operator or when
        an error occurs that requires cancellation.
        
        Args:
            context: Blender context
        """
        try:
            wm = context.window_manager
            if self._timer:
                wm.event_timer_remove(self._timer)
                self._timer = None

            if self._controller:
                self._controller.cleanup()
                self._controller = None

            context.scene.cle_live_modal_running = False

            self.report({'INFO'}, "Stopped live inputs.")
            
        except Exception as e:
            logger.error(f"Error cancelling live controller inputs: {e}")

class CLE_OT_RecordControllerInputs(bpy.types.Operator):
    """
    Operator for recording controller inputs with automatic keyframing.
    
    This modal operator combines live controller input polling with automatic
    keyframe creation and timeline playback. It's designed for:
    - Recording controller input animations
    - Creating keyframed sequences for later editing
    - Capturing complex controller performances
    
    The operator automatically:
    - Starts timeline playback
    - Polls controller inputs at 60Hz
    - Creates keyframes for all controller properties on each frame
    - Manages frame change handlers for keyframing
    
    Class Attributes:
        _timer: Blender timer for modal updates
        _controller: SDL2Controller instance for input polling
    """
    bl_idname = "wm.cle_record_controller_inputs"
    bl_label = "Record Controller Inputs"
    bl_description = "Start/stop recording controller inputs with keyframes"

    _timer = None
    _controller: Optional[SDL2Controller] = None

    def modal(self, context, event):
        """
        Modal operator update loop for recording controller inputs.
        
        Similar to the live input modal but specifically designed for recording.
        The actual keyframing happens in the frame change handler, while this
        modal loop focuses on continuous input polling.
        
        Args:
            context: Blender context
            event: Blender event (timer, keyboard, etc.)
            
        Returns:
            set: Blender operator return status
                - {'PASS_THROUGH'}: Continue modal operation
                - {'CANCELLED'}: Stop recording and cleanup
        """
        try:
            if event.type == 'TIMER':
                if self._controller and self._controller.is_connected():
                    reader = get_reader()
                    if reader:
                        success = self._controller.poll_inputs(reader)
                        if success:
                            # Trigger driver updates
                            reader.location = reader.location
                        else:
                            logger.warning("Failed to poll controller inputs during recording")
                else:
                    logger.warning("Controller disconnected during recording")
                    self.cancel(context)
                    return {'CANCELLED'}
                    
            if not context.scene.cle_record_modal_running or event.type in {'ESC'}:
                self.cancel(context)
                return {'CANCELLED'}
                
            return {'PASS_THROUGH'}
            
        except Exception as e:
            logger.error(f"Error in record controller modal: {e}")
            self.cancel(context)
            return {'CANCELLED'}

    def execute(self, context):
        """
        Initialize and start the controller input recording operator.
        
        Sets up everything needed for recording:
        - Controller initialization
        - Frame change handler registration
        - Timeline playback
        - Modal timer setup
        
        Args:
            context: Blender context
            
        Returns:
            set: Blender operator return status
                - {'RUNNING_MODAL'}: Successfully started recording
                - {'CANCELLED'}: Failed to start, operation cancelled
        """
        try:
            # Create reader object
            reader = create_reader()
            if not reader:
                self.report({'ERROR'}, "Failed to create reader object")
                return {'CANCELLED'}

            # Stop live mode if running
            if context.scene.cle_live_modal_running:
                context.scene.cle_live_modal_running = False
        
            # Toggle record mode
            if context.scene.cle_record_modal_running:
                context.scene.cle_record_modal_running = False
                return {'CANCELLED'}
            
            # Initialize controller
            try:
                self._controller = SDL2Controller()
                if not self._controller.is_connected():
                    self.report({'WARNING'}, "No controller detected")
                    # Continue anyway in case controller gets connected later
                    
            except Exception as e:
                logger.error(f"Failed to initialize controller: {e}")
                self.report({'ERROR'}, f"Controller initialization failed: {e}")
                return {'CANCELLED'}

            # Add keyframing handler
            try:
                if keyframe_inputs not in bpy.app.handlers.frame_change_pre:
                    bpy.app.handlers.frame_change_pre.append(keyframe_inputs)
            except Exception as e:
                logger.warning(f"Failed to add keyframe handler: {e}")

            # Set up timer and modal
            wm = context.window_manager
            self._timer = wm.event_timer_add(time_step=1/60, window=context.window)
            wm.modal_handler_add(self)

            # Start timeline playback
            try:
                bpy.ops.screen.animation_play()
            except Exception as e:
                logger.warning(f"Failed to start animation playback: {e}")

            # Set flag
            context.scene.cle_record_modal_running = True

            # Create node group
            try:
                bpy.ops.wm.cle_create_nodegroup()
            except Exception as e:
                logger.warning(f"Failed to create node group: {e}")
                # Continue without node group

            self.report({'INFO'}, f"Started recording controller inputs: {self._controller.controller_name if self._controller else 'No controller'}")
            return {'RUNNING_MODAL'}
            
        except Exception as e:
            logger.error(f"Error starting record controller inputs: {e}")
            self.report({'ERROR'}, f"Failed to start recording: {e}")
            return {'CANCELLED'}

    def cancel(self, context):
        """
        Clean up and cancel the recording controller input operator.
        
        Performs comprehensive cleanup:
        - Stops timeline playback
        - Removes frame change handlers
        - Cleans up controller resources
        - Removes timers
        - Resets UI state
        
        Args:
            context: Blender context
        """
        try:
            wm = context.window_manager
            if self._timer:
                wm.event_timer_remove(self._timer)
                self._timer = None

            # Stop timeline if it is playing
            try:
                if bpy.context.screen.is_animation_playing:
                    bpy.ops.screen.animation_play()
            except Exception as e:
                logger.warning(f"Error stopping animation playback: {e}")

            # Remove keyframe handler
            try:
                if keyframe_inputs in bpy.app.handlers.frame_change_pre:
                    bpy.app.handlers.frame_change_pre.remove(keyframe_inputs)
            except Exception as e:
                logger.warning(f"Error removing keyframe handler: {e}")

            if self._controller:
                self._controller.cleanup()
                self._controller = None

            context.scene.cle_record_modal_running = False

            self.report({'INFO'}, "Stopped recording inputs.")
            
        except Exception as e:
            logger.error(f"Error cancelling record controller inputs: {e}")
