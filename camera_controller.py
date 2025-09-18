"""
Camera Controller module for Blender Controller Link Extended.
Handles camera control functionality using controller inputs.
"""

import bpy
import mathutils
import logging
from typing import Optional, Tuple
from .controller import get_reader

# Set up logging
logger = logging.getLogger(__name__)

class CameraController:
    """
    Camera controller that maps controller inputs to camera movements.
    
    This class handles both free camera mode and look-at-target mode,
    providing smooth camera control based on controller inputs.
    """
    
    def __init__(self):
        self.camera_object: Optional[bpy.types.Object] = None
        self.target_object: Optional[bpy.types.Object] = None
        self.sensitivity: float = 1.0
        self.smoothing: float = 0.1
        self.last_rotation: Optional[mathutils.Vector] = None
        self.last_location: Optional[mathutils.Vector] = None
        
    def setup_camera(self, camera_obj: bpy.types.Object, target_obj: Optional[bpy.types.Object] = None):
        """
        Set up the camera and target objects.
        
        Args:
            camera_obj: Camera object to control
            target_obj: Optional target object to look at
        """
        self.camera_object = camera_obj
        self.target_object = target_obj
        
        if camera_obj:
            self.last_rotation = camera_obj.rotation_euler.copy()
            self.last_location = camera_obj.location.copy()
            
    def update_from_scene_properties(self, scene: bpy.types.Scene):
        """
        Update camera controller settings from scene properties.
        
        Args:
            scene: Blender scene containing the properties
        """
        self.camera_object = getattr(scene, 'cle_camera_object', None)
        self.target_object = getattr(scene, 'cle_target_object', None)
        self.sensitivity = getattr(scene, 'cle_camera_sensitivity', 1.0)
        self.smoothing = getattr(scene, 'cle_camera_smoothing', 0.1)
        
    def process_inputs(self, reader_object: bpy.types.Object) -> bool:
        """
        Process controller inputs and update camera accordingly.
        
        Args:
            reader_object: Object containing controller input properties
            
        Returns:
            bool: True if processing was successful
        """
        if not self.camera_object or not reader_object:
            return False
            
        try:
            # Get controller inputs
            inputs = self._get_controller_inputs(reader_object)
            if not inputs:
                return False
                
            # Apply camera movement based on mode
            if self.target_object:
                self._update_look_at_camera(inputs)
            else:
                self._update_free_camera(inputs)
                
            return True
            
        except Exception as e:
            logger.error(f"Error processing camera inputs: {e}")
            return False
    
    def _get_controller_inputs(self, reader_object: bpy.types.Object) -> Optional[dict]:
        """
        Extract relevant controller inputs for camera control.
        
        Args:
            reader_object: Object containing controller properties
            
        Returns:
            dict: Dictionary of input values or None if no inputs found
        """
        inputs = {}
        
        # Common controller mappings
        input_mappings = {
            'leftstick_x': 'controller_axis_leftstick_x',
            'leftstick_y': 'controller_axis_leftstick_y', 
            'rightstick_x': 'controller_axis_rightstick_x',
            'rightstick_y': 'controller_axis_rightstick_y',
            'lefttrigger': 'controller_axis_lefttrigger',
            'righttrigger': 'controller_axis_righttrigger',
            'dpad_up': 'controller_button_dpad_up',
            'dpad_down': 'controller_button_dpad_down',
            'dpad_left': 'controller_button_dpad_left',
            'dpad_right': 'controller_button_dpad_right'
        }
        
        # Try to get inputs, fallback to generic names if specific ones don't exist
        for input_name, prop_name in input_mappings.items():
            if prop_name in reader_object:
                inputs[input_name] = reader_object[prop_name]
            else:
                # Try generic axis/button names
                generic_name = prop_name.replace('leftstick', 'axis_0').replace('rightstick', 'axis_1')
                generic_name = generic_name.replace('lefttrigger', 'axis_2').replace('righttrigger', 'axis_3')
                generic_name = generic_name.replace('dpad_up', 'button_0').replace('dpad_down', 'button_1')
                generic_name = generic_name.replace('dpad_left', 'button_2').replace('dpad_right', 'button_3')
                
                if generic_name in reader_object:
                    inputs[input_name] = reader_object[generic_name]
        
        return inputs if inputs else None
    
    def _update_free_camera(self, inputs: dict):
        """
        Update camera in free mode (no target).
        
        Args:
            inputs: Dictionary of controller input values
        """
        if not self.camera_object:
            return
            
        # Get current camera state
        camera = self.camera_object
        current_rotation = camera.rotation_euler.copy()
        current_location = camera.location.copy()
        
        # Initialize last values if not set
        if self.last_rotation is None:
            self.last_rotation = current_rotation.copy()
        if self.last_location is None:
            self.last_location = current_location.copy()
        
        # Calculate movement deltas
        delta_rotation = mathutils.Vector((0, 0, 0))
        delta_location = mathutils.Vector((0, 0, 0))
        
        # Right stick for rotation (pitch/yaw)
        if 'rightstick_x' in inputs:
            delta_rotation.z = inputs['rightstick_x'] * self.sensitivity * 0.1
        if 'rightstick_y' in inputs:
            delta_rotation.x = inputs['rightstick_y'] * self.sensitivity * 0.1
            
        # Left stick for movement (forward/back, strafe)
        if 'leftstick_y' in inputs:
            # Forward/back movement
            forward = camera.matrix_world.to_3x3() @ mathutils.Vector((0, 0, -1))
            delta_location += forward * inputs['leftstick_y'] * self.sensitivity * 0.1
            
        if 'leftstick_x' in inputs:
            # Strafe movement
            right = camera.matrix_world.to_3x3() @ mathutils.Vector((1, 0, 0))
            delta_location += right * inputs['leftstick_x'] * self.sensitivity * 0.1
            
        # Triggers for up/down movement
        if 'lefttrigger' in inputs:
            delta_location.z -= inputs['lefttrigger'] * self.sensitivity * 0.1
        if 'righttrigger' in inputs:
            delta_location.z += inputs['righttrigger'] * self.sensitivity * 0.1
        
        # Apply smoothing
        smoothed_rotation = self._apply_smoothing(
            self.last_rotation, 
            current_rotation + delta_rotation,
            self.smoothing
        )
        smoothed_location = self._apply_smoothing(
            self.last_location,
            current_location + delta_location,
            self.smoothing
        )
        
        # Update camera
        camera.rotation_euler = smoothed_rotation
        camera.location = smoothed_location
        
        # Store for next frame
        self.last_rotation = smoothed_rotation.copy()
        self.last_location = smoothed_location.copy()
    
    def _update_look_at_camera(self, inputs: dict):
        """
        Update camera in look-at-target mode.
        
        Args:
            inputs: Dictionary of controller input values
        """
        if not self.camera_object or not self.target_object:
            return
            
        camera = self.camera_object
        target = self.target_object
        
        # Get current camera state
        current_location = camera.location.copy()
        
        # Initialize last location if not set
        if self.last_location is None:
            self.last_location = current_location.copy()
        
        # Calculate orbit movement
        delta_location = mathutils.Vector((0, 0, 0))
        
        # Right stick for orbiting around target
        if 'rightstick_x' in inputs:
            # Horizontal orbit
            direction = current_location - target.location
            direction.normalize()
            perpendicular = direction.cross(mathutils.Vector((0, 0, 1)))
            perpendicular.normalize()
            delta_location += perpendicular * inputs['rightstick_x'] * self.sensitivity * 0.1
            
        if 'rightstick_y' in inputs:
            # Vertical orbit
            direction = current_location - target.location
            direction.normalize()
            perpendicular = direction.cross(mathutils.Vector((1, 0, 0)))
            perpendicular.normalize()
            delta_location += perpendicular * inputs['rightstick_y'] * self.sensitivity * 0.1
        
        # Left stick for distance adjustment
        if 'leftstick_y' in inputs:
            direction = current_location - target.location
            direction.normalize()
            delta_location += direction * inputs['leftstick_y'] * self.sensitivity * 0.1
        
        # Apply smoothing
        smoothed_location = self._apply_smoothing(
            self.last_location,
            current_location + delta_location,
            self.smoothing
        )
        
        # Update camera location
        camera.location = smoothed_location
        
        # Make camera look at target
        direction = target.location - camera.location
        camera.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
        
        # Store for next frame
        self.last_location = smoothed_location.copy()
    
    def _apply_smoothing(self, last_value: mathutils.Vector, target_value: mathutils.Vector, smoothing: float) -> mathutils.Vector:
        """
        Apply smoothing interpolation between last and target values.
        
        Args:
            last_value: Previous value
            target_value: Target value
            smoothing: Smoothing factor (0-1)
            
        Returns:
            mathutils.Vector: Smoothed value
        """
        if smoothing <= 0:
            return target_value
        elif smoothing >= 1:
            return last_value
        else:
            return last_value.lerp(target_value, smoothing)

# Global camera controller instance
_camera_controller = CameraController()

def get_camera_controller() -> CameraController:
    """
    Get the global camera controller instance.
    
    Returns:
        CameraController: The global camera controller instance
    """
    return _camera_controller

def update_camera_from_controller(scene: bpy.types.Scene) -> bool:
    """
    Update camera based on controller inputs and scene settings.
    
    Args:
        scene: Blender scene containing settings and controller data
        
    Returns:
        bool: True if update was successful
    """
    try:
        # Check if camera controller is enabled
        if not getattr(scene, 'cle_camera_controller_enabled', False):
            return False
            
        # Update controller settings from scene
        _camera_controller.update_from_scene_properties(scene)
        
        # Get controller data
        reader_object = get_reader()
        if not reader_object:
            return False
            
        # Process inputs and update camera
        return _camera_controller.process_inputs(reader_object)
        
    except Exception as e:
        logger.error(f"Error updating camera from controller: {e}")
        return False