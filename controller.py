"""
Controller handling module for Blender Controller Link Extended.
Provides SDL2-based controller input with robust error handling and resource management.
"""

import bpy
import sdl2
import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Set up logging
logger = logging.getLogger(__name__)

class ControllerError(Exception):
    """
    Custom exception for controller-related errors.
    
    This exception is raised when SDL2 operations fail or when
    controller-specific errors occur that need to be handled
    gracefully by the calling code.
    """
    pass

class SDL2Controller:
    """
    SDL2-based controller handler with proper resource management and error handling.
    
    This class encapsulates all SDL2 controller operations, providing a clean interface
    for detecting, connecting to, and polling game controllers or joysticks. It handles
    both standardized game controllers (preferred) and raw joysticks (fallback).
    
    Features:
    - Automatic controller detection with fallback mechanisms
    - Proper SDL2 resource management and cleanup
    - Real-time connection status monitoring
    - Input value normalization and validation
    - Comprehensive error handling and logging
    
    Attributes:
        controller: SDL2 game controller object (if available)
        joystick: SDL2 joystick object (fallback)
        controller_name: Human-readable name of the connected device
        is_gamecontroller: True if using standardized game controller
        is_initialized: True if SDL2 was successfully initialized
    """
    
    def __init__(self):
        """
        Initialize the SDL2 controller handler.
        
        Automatically initializes SDL2, detects available controllers,
        and connects to the first suitable device found.
        
        Raises:
            ControllerError: If SDL2 initialization fails
        """
        self.controller: Optional[Any] = None
        self.joystick: Optional[Any] = None
        self.controller_name: str = ""
        self.is_gamecontroller: bool = False
        self.is_initialized: bool = False
        self._init_sdl2()
        self._find_controller()
    
    def _init_sdl2(self) -> None:
        """
        Initialize SDL2 subsystems required for controller input.
        
        Initializes both game controller and joystick subsystems to ensure
        compatibility with various input devices.
        
        Raises:
            ControllerError: If SDL2 initialization fails
        """
        try:
            result = sdl2.SDL_Init(sdl2.SDL_INIT_GAMECONTROLLER | sdl2.SDL_INIT_JOYSTICK)
            if result != 0:
                error_msg = sdl2.SDL_GetError().decode('utf-8') if sdl2.SDL_GetError() else "Unknown SDL2 error"
                raise ControllerError(f"Failed to initialize SDL2: {error_msg}")
            self.is_initialized = True
            logger.info("SDL2 initialized successfully")
        except Exception as e:
            logger.error(f"SDL2 initialization failed: {e}")
            raise ControllerError(f"SDL2 initialization failed: {e}")
    
    def _find_controller(self) -> None:
        """
        Find and connect to the first available controller.
        
        Searches for controllers in order of preference:
        1. Game controllers (standardized button/axis mapping)
        2. Raw joysticks (fallback with numeric indices)
        
        The first successfully opened device is used. If no devices
        are found, the controller remains unconnected but the object
        is still usable for later connection attempts.
        
        Raises:
            ControllerError: If SDL2 is not initialized
        """
        if not self.is_initialized:
            raise ControllerError("SDL2 not initialized")
        
        try:
            num_joysticks = sdl2.SDL_NumJoysticks()
            if num_joysticks <= 0:
                logger.warning("No joysticks/controllers detected")
                return
            
            # Try to find a game controller first (preferred)
            for i in range(num_joysticks):
                try:
                    if sdl2.SDL_IsGameController(i):
                        self.controller = sdl2.SDL_GameControllerOpen(i)
                        if self.controller:
                            name_ptr = sdl2.SDL_GameControllerName(self.controller)
                            self.controller_name = name_ptr.decode("utf-8") if name_ptr else f"Controller {i}"
                            self.is_gamecontroller = True
                            logger.info(f"Connected to game controller: {self.controller_name}")
                            return
                except Exception as e:
                    logger.warning(f"Failed to open game controller {i}: {e}")
                    continue
            
            # Fallback to raw joystick if no game controller found
            try:
                self.joystick = sdl2.SDL_JoystickOpen(0)
                if self.joystick:
                    name_ptr = sdl2.SDL_JoystickName(self.joystick)
                    self.controller_name = name_ptr.decode("utf-8") if name_ptr else "Joystick 0"
                    logger.info(f"Connected to joystick: {self.controller_name}")
                else:
                    logger.warning("Failed to open first joystick")
            except Exception as e:
                logger.error(f"Failed to open joystick: {e}")
                
        except Exception as e:
            logger.error(f"Error while finding controller: {e}")
            raise ControllerError(f"Failed to find controller: {e}")
    
    def is_connected(self) -> bool:
        """
        Check if a controller is currently connected and available.
        
        This method actively checks the SDL2 connection status,
        which can detect if a controller was unplugged during use.
        
        Returns:
            bool: True if a controller is connected and responsive
        """
        try:
            if self.is_gamecontroller and self.controller:
                return sdl2.SDL_GameControllerGetAttached(self.controller) == 1
            elif self.joystick:
                return sdl2.SDL_JoystickGetAttached(self.joystick) == 1
            return False
        except Exception as e:
            logger.warning(f"Error checking controller connection: {e}")
            return False
    
    def poll_inputs(self, reader_object: bpy.types.Object) -> bool:
        """
        Poll all controller inputs and update the reader object properties.
        
        This is the main input polling method that reads all available
        axes and buttons from the connected controller and stores them
        as custom properties on the provided Blender object.
        
        Property naming convention:
        - Axes: 'controller_axis_{name}' or 'controller_axis_{index}'
        - Buttons: 'controller_button_{name}' or 'controller_button_{index}'
        
        Axis values are normalized to [-1.0, 1.0] range.
        Button values are boolean (True/False).
        
        Args:
            reader_object: Blender object to store controller properties
            
        Returns:
            bool: True if polling was successful, False on error
        """
        """
        Poll controller inputs and update the reader object properties.
        
        Args:
            reader_object: Blender object to store controller data
            
        Returns:
            bool: True if successful, False if error occurred
        """
        if not reader_object:
            logger.warning("No reader object provided")
            return False
        
        if not self.is_connected():
            logger.warning("Controller not connected")
            return False
        
        try:
            sdl2.SDL_PumpEvents()
            
            if self.is_gamecontroller and self.controller:
                return self._poll_gamecontroller(reader_object)
            elif self.joystick:
                return self._poll_joystick(reader_object)
            
            return False
            
        except Exception as e:
            logger.error(f"Error polling controller inputs: {e}")
            return False
    
    def _poll_gamecontroller(self, reader_object: bpy.types.Object) -> bool:
        """
        Poll standardized game controller inputs.
        
        Uses SDL2's game controller API which provides standardized
        button and axis names (e.g., 'leftstick_x', 'button_a') that
        are consistent across different controller brands.
        
        Args:
            reader_object: Blender object to store properties
            
        Returns:
            bool: True if successful, False on error
        """
        try:
            # Poll axes
            for axis in range(sdl2.SDL_CONTROLLER_AXIS_MAX):
                try:
                    if sdl2.SDL_GameControllerHasAxis(self.controller, axis):
                        name_ptr = sdl2.SDL_GameControllerGetStringForAxis(axis)
                        if name_ptr:
                            name = name_ptr.decode("utf-8")
                            prop_id = f"controller_axis_{name}"
                            raw = sdl2.SDL_GameControllerGetAxis(self.controller, axis)
                            value = max(-1.0, min(1.0, raw / 32767.0))
                            reader_object[prop_id] = value
                except Exception as e:
                    logger.warning(f"Error polling axis {axis}: {e}")
                    continue
            
            # Poll buttons
            for button in range(sdl2.SDL_CONTROLLER_BUTTON_MAX):
                try:
                    if sdl2.SDL_GameControllerHasButton(self.controller, button):
                        name_ptr = sdl2.SDL_GameControllerGetStringForButton(button)
                        if name_ptr:
                            name = name_ptr.decode("utf-8")
                            prop_id = f"controller_button_{name}"
                            pressed = bool(sdl2.SDL_GameControllerGetButton(self.controller, button))
                            reader_object[prop_id] = pressed
                except Exception as e:
                    logger.warning(f"Error polling button {button}: {e}")
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"Error in _poll_gamecontroller: {e}")
            return False
    
    def _poll_joystick(self, reader_object: bpy.types.Object) -> bool:
        """
        Poll raw joystick inputs as fallback method.
        
        Uses SDL2's joystick API with numeric indices for axes and buttons.
        This is used when a device isn't recognized as a standardized
        game controller but can still provide input.
        
        Args:
            reader_object: Blender object to store properties
            
        Returns:
            bool: True if successful, False on error
        """
        try:
            # Poll axes
            num_axes = sdl2.SDL_JoystickNumAxes(self.joystick)
            for axis in range(num_axes):
                try:
                    raw = sdl2.SDL_JoystickGetAxis(self.joystick, axis)
                    value = max(-1.0, min(1.0, raw / 32767.0))
                    prop_id = f"controller_axis_{axis}"
                    reader_object[prop_id] = value
                except Exception as e:
                    logger.warning(f"Error polling joystick axis {axis}: {e}")
                    continue
            
            # Poll buttons
            num_buttons = sdl2.SDL_JoystickNumButtons(self.joystick)
            for button in range(num_buttons):
                try:
                    pressed = bool(sdl2.SDL_JoystickGetButton(self.joystick, button))
                    prop_id = f"controller_button_{button}"
                    reader_object[prop_id] = pressed
                except Exception as e:
                    logger.warning(f"Error polling joystick button {button}: {e}")
                    continue
            
            return True
            
        except Exception as e:
            logger.error(f"Error in _poll_joystick: {e}")
            return False
    
    def cleanup(self) -> None:
        """
        Clean up all SDL2 resources and shut down subsystems.
        
        This method should be called when the controller is no longer needed
        to prevent resource leaks. It's safe to call multiple times.
        
        Note: After cleanup, the controller object cannot be reused.
              A new instance must be created for further controller access.
        """
        try:
            if self.controller:
                sdl2.SDL_GameControllerClose(self.controller)
                self.controller = None
                logger.info("Game controller closed")
            
            if self.joystick:
                sdl2.SDL_JoystickClose(self.joystick)
                self.joystick = None
                logger.info("Joystick closed")
            
            if self.is_initialized:
                sdl2.SDL_Quit()
                self.is_initialized = False
                logger.info("SDL2 quit")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """
        Destructor to ensure SDL2 resources are cleaned up.
        
        This provides a safety net in case cleanup() wasn't called explicitly.
        However, explicit cleanup is preferred for deterministic resource management.
        """
        self.cleanup()

@contextmanager
def controller_context():
    """
    Context manager for safe controller usage with automatic cleanup.
    
    This context manager ensures that SDL2 resources are properly cleaned up
    even if an exception occurs during controller operations.
    
    Example:
        with controller_context() as controller:
            if controller.is_connected():
                controller.poll_inputs(reader_object)
    
    Yields:
        SDL2Controller: Initialized controller instance
    
    Raises:
        ControllerError: If controller initialization fails
    """
    controller = None
    try:
        controller = SDL2Controller()
        yield controller
    except Exception as e:
        logger.error(f"Error in controller context: {e}")
        raise
    finally:
        if controller:
            controller.cleanup()

def get_reader() -> Optional[bpy.types.Object]:
    """
    Get the CLE_reader object that stores controller properties.
    
    The CLE_reader is a special Blender object (without mesh data) that
    serves as a container for custom properties representing controller inputs.
    These properties can then be used in drivers, constraints, or node groups.
    
    Returns:
        Optional[bpy.types.Object]: The CLE_reader object if it exists, None otherwise
    """
    try:
        return bpy.data.objects.get("CLE_reader")
    except Exception as e:
        logger.error(f"Error getting reader object: {e}")
        return None

def create_reader() -> Optional[bpy.types.Object]:
    """
    Create or get the CLE_reader object for storing controller data.
    
    If the CLE_reader object doesn't exist, creates a new empty object
    with 'use_fake_user' enabled to prevent it from being deleted when
    not referenced by the scene.
    
    Returns:
        Optional[bpy.types.Object]: The CLE_reader object, or None on error
    """
    try:
        cle_reader = get_reader()
        if cle_reader is None:
            cle_reader = bpy.data.objects.new("CLE_reader", None)
            cle_reader.use_fake_user = True
            logger.info("Created new CLE_reader object")
        return cle_reader
    except Exception as e:
        logger.error(f"Error creating reader object: {e}")
        return None

def trigger_reader_update(reader_object: bpy.types.Object) -> None:
    """
    Trigger an update on the reader object to force driver re-evaluation.
    
    Blender's driver system sometimes needs a 'kick' to update when
    custom properties change. This function provides that trigger by
    setting the object's location to itself, which is a harmless operation
    that forces the dependency graph to update.
    
    Args:
        reader_object: The CLE_reader object to update
    """
    try:
        if reader_object:
            # Trigger update by setting location to itself
            reader_object.location = reader_object.location
    except Exception as e:
        logger.warning(f"Error triggering reader update: {e}")
