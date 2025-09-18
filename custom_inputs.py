"""
Custom Inputs module for Blender Controller Link Extended.
Handles creation, editing, and management of custom controller input mappings.
"""

import bpy
import logging
from typing import List, Dict, Any, Optional
from bpy.types import PropertyGroup
from bpy.props import (
    StringProperty, 
    EnumProperty, 
    FloatProperty, 
    IntProperty, 
    BoolProperty,
    CollectionProperty
)

# Set up logging
logger = logging.getLogger(__name__)

class CLE_CustomInput(PropertyGroup):
    """
    Property group for storing custom input configuration.
    
    This class defines the structure for custom controller inputs,
    including all the customizable parameters like name, mapping,
    data type, accumulation type, etc.
    """
    
    # Basic properties
    name: StringProperty(
        name="Name",
        description="Display name for this custom input",
        default="Custom Input"
    )
    
    mapped_input: StringProperty(
        name="Mapped Input",
        description="Controller input to map (e.g., 'controller_axis_leftstick_x')",
        default="controller_axis_leftstick_x"
    )
    
    data_type: EnumProperty(
        name="Data Type",
        description="Type of data this input represents",
        items=[
            ('FLOAT', "Float", "Floating point number"),
            ('INT', "Integer", "Whole number"),
            ('BOOL', "Boolean", "True/False value"),
            ('VECTOR', "Vector", "3D Vector"),
            ('ROTATION', "Rotation", "Rotation value")
        ],
        default='FLOAT'
    )
    
    subtype: EnumProperty(
        name="Subtype",
        description="Subtype classification for the data",
        items=[
            ('NONE', "None", "No specific subtype"),
            ('FACTOR', "Factor", "Multiplier factor"),
            ('DISTANCE', "Distance", "Distance measurement"),
            ('ANGLE', "Angle", "Angle measurement"),
            ('PERCENTAGE', "Percentage", "Percentage value"),
            ('VELOCITY', "Velocity", "Speed measurement"),
            ('ACCELERATION', "Acceleration", "Acceleration measurement"),
            ('FORCE', "Force", "Force measurement"),
            ('TIME', "Time", "Time measurement"),
            ('TEMPERATURE', "Temperature", "Temperature measurement")
        ],
        default='NONE'
    )
    
    accumulation_type: EnumProperty(
        name="Accumulation Type",
        description="How input values are accumulated over time",
        items=[
            ('CONTINUOUS', "Continuous", "Continuous accumulation"),
            ('ABSOLUTE', "Absolute", "Absolute values only"),
            ('TOGGLE', "Toggle", "Toggle on/off"),
            ('CYCLE', "Cycle", "Cyclic values"),
            ('PULSE', "Pulse", "Pulse detection"),
            ('THRESHOLD', "Threshold", "Threshold-based")
        ],
        default='CONTINUOUS'
    )
    
    # Range and limits
    min_value: FloatProperty(
        name="Min Value",
        description="Minimum value for this input",
        default=-1.0,
        soft_min=-10.0,
        soft_max=10.0
    )
    
    max_value: FloatProperty(
        name="Max Value",
        description="Maximum value for this input",
        default=1.0,
        soft_min=-10.0,
        soft_max=10.0
    )
    
    # Dead zones for continuous inputs
    dead_zone_min: FloatProperty(
        name="Dead Zone Min",
        description="Minimum dead zone threshold",
        default=-0.1,
        soft_min=-1.0,
        soft_max=1.0
    )
    
    dead_zone_max: FloatProperty(
        name="Dead Zone Max",
        description="Maximum dead zone threshold",
        default=0.1,
        soft_min=-1.0,
        soft_max=1.0
    )
    
    # Smoothing
    smoothing_speed: FloatProperty(
        name="Smoothing Speed",
        description="Speed of smoothing interpolation",
        default=0.1,
        min=0.001,
        max=1.0,
        step=0.01
    )
    
    # Additional options
    invert_input: BoolProperty(
        name="Invert Input",
        description="Invert the input values",
        default=False
    )
    
    clamp_values: BoolProperty(
        name="Clamp Values",
        description="Clamp values to min/max range",
        default=True
    )
    
    # Advanced settings
    sensitivity: FloatProperty(
        name="Sensitivity",
        description="Input sensitivity multiplier",
        default=1.0,
        min=0.1,
        max=10.0,
        step=0.1
    )
    
    offset: FloatProperty(
        name="Offset",
        description="Value offset to apply",
        default=0.0,
        soft_min=-10.0,
        soft_max=10.0
    )

class CLE_OT_AddCustomInput(bpy.types.Operator):
    """
    Operator to add a new custom input.
    
    Opens a popup dialog for configuring the new custom input.
    """
    bl_idname = "wm.cle_add_custom_input"
    bl_label = "Add Custom Input"
    bl_description = "Add a new custom controller input mapping"
    
    def draw(self, context):
        """Draw the custom input configuration dialog."""
        layout = self.layout
        
        # Create a temporary custom input for editing
        if not hasattr(context.scene, '_temp_custom_input'):
            context.scene._temp_custom_input = CLE_CustomInput()
        
        temp_input = context.scene._temp_custom_input
        
        # Basic configuration
        layout.label(text="Custom Input Configuration", icon='SETTINGS')
        layout.separator()
        
        # Name
        layout.prop(temp_input, "name")
        
        # Mapped input selection
        layout.label(text="Controller Input:")
        cle_reader = bpy.data.objects.get("CLE_reader")
        if cle_reader:
            # Get available controller inputs
            available_inputs = []
            for prop_name in cle_reader.keys():
                if prop_name.startswith("controller_"):
                    display_name = prop_name.replace("controller_", "").replace("_", " ").title()
                    available_inputs.append((prop_name, display_name, ""))
            
            if available_inputs:
                layout.prop_search(temp_input, "mapped_input", context.scene, "cle_available_inputs")
            else:
                layout.prop(temp_input, "mapped_input")
        else:
            layout.prop(temp_input, "mapped_input")
        
        layout.separator()
        
        # Data type and subtype
        row = layout.row()
        row.prop(temp_input, "data_type")
        row.prop(temp_input, "subtype")
        
        # Accumulation type
        layout.prop(temp_input, "accumulation_type")
        
        layout.separator()
        
        # Range settings
        layout.label(text="Range Settings:")
        row = layout.row()
        row.prop(temp_input, "min_value")
        row.prop(temp_input, "max_value")
        
        # Dead zones
        layout.label(text="Dead Zones:")
        row = layout.row()
        row.prop(temp_input, "dead_zone_min")
        row.prop(temp_input, "dead_zone_max")
        
        layout.separator()
        
        # Advanced settings
        layout.label(text="Advanced Settings:")
        layout.prop(temp_input, "smoothing_speed")
        layout.prop(temp_input, "sensitivity")
        layout.prop(temp_input, "offset")
        
        # Options
        layout.label(text="Options:")
        row = layout.row()
        row.prop(temp_input, "invert_input")
        row.prop(temp_input, "clamp_values")
    
    def invoke(self, context, event):
        """Initialize the dialog."""
        # Initialize temporary custom input with defaults
        if not hasattr(context.scene, '_temp_custom_input'):
            context.scene._temp_custom_input = CLE_CustomInput()
        
        # Update available inputs list
        self._update_available_inputs(context)
        
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def _update_available_inputs(self, context):
        """Update the list of available controller inputs."""
        cle_reader = bpy.data.objects.get("CLE_reader")
        if cle_reader:
            available_inputs = []
            for prop_name in cle_reader.keys():
                if prop_name.startswith("controller_"):
                    display_name = prop_name.replace("controller_", "").replace("_", " ").title()
                    available_inputs.append((prop_name, display_name, ""))
            
            # Store in scene for prop_search
            context.scene.cle_available_inputs = available_inputs
    
    def check(self, context):
        """Validate the input configuration."""
        return True
    
    def execute(self, context):
        """Add the custom input to the scene."""
        try:
            temp_input = context.scene._temp_custom_input
            
            # Create new custom input
            custom_inputs = getattr(context.scene, 'cle_custom_inputs', [])
            new_input = custom_inputs.add()
            
            # Copy properties from temporary input
            new_input.name = temp_input.name
            new_input.mapped_input = temp_input.mapped_input
            new_input.data_type = temp_input.data_type
            new_input.subtype = temp_input.subtype
            new_input.accumulation_type = temp_input.accumulation_type
            new_input.min_value = temp_input.min_value
            new_input.max_value = temp_input.max_value
            new_input.dead_zone_min = temp_input.dead_zone_min
            new_input.dead_zone_max = temp_input.dead_zone_max
            new_input.smoothing_speed = temp_input.smoothing_speed
            new_input.invert_input = temp_input.invert_input
            new_input.clamp_values = temp_input.clamp_values
            new_input.sensitivity = temp_input.sensitivity
            new_input.offset = temp_input.offset
            
            # Clean up temporary input
            if hasattr(context.scene, '_temp_custom_input'):
                delattr(context.scene, '_temp_custom_input')
            
            self.report({'INFO'}, f"Added custom input: {new_input.name}")
            return {'FINISHED'}
            
        except Exception as e:
            logger.error(f"Error adding custom input: {e}")
            self.report({'ERROR'}, f"Failed to add custom input: {e}")
            return {'CANCELLED'}

class CLE_OT_EditCustomInput(bpy.types.Operator):
    """
    Operator to edit an existing custom input.
    """
    bl_idname = "wm.cle_edit_custom_input"
    bl_label = "Edit Custom Input"
    bl_description = "Edit an existing custom controller input mapping"
    
    index: IntProperty(
        name="Index",
        description="Index of the custom input to edit",
        default=0
    )
    
    def invoke(self, context, event):
        """Open the edit dialog."""
        return context.window_manager.invoke_props_dialog(self, width=400)
    
    def draw(self, context):
        """Draw the edit dialog."""
        custom_inputs = getattr(context.scene, 'cle_custom_inputs', [])
        if self.index < len(custom_inputs):
            custom_input = custom_inputs[self.index]
            
            layout = self.layout
            layout.label(text=f"Edit: {custom_input.name}", icon='EDIT')
            layout.separator()
            
            # Same fields as add dialog
            layout.prop(custom_input, "name")
            layout.prop(custom_input, "mapped_input")
            
            row = layout.row()
            row.prop(custom_input, "data_type")
            row.prop(custom_input, "subtype")
            
            layout.prop(custom_input, "accumulation_type")
            
            layout.separator()
            layout.label(text="Range Settings:")
            row = layout.row()
            row.prop(custom_input, "min_value")
            row.prop(custom_input, "max_value")
            
            layout.label(text="Dead Zones:")
            row = layout.row()
            row.prop(custom_input, "dead_zone_min")
            row.prop(custom_input, "dead_zone_max")
            
            layout.separator()
            layout.label(text="Advanced Settings:")
            layout.prop(custom_input, "smoothing_speed")
            layout.prop(custom_input, "sensitivity")
            layout.prop(custom_input, "offset")
            
            layout.label(text="Options:")
            row = layout.row()
            row.prop(custom_input, "invert_input")
            row.prop(custom_input, "clamp_values")
    
    
    def execute(self, context):
        """Save the edited custom input."""
        try:
            custom_inputs = getattr(context.scene, 'cle_custom_inputs', [])
            if self.index < len(custom_inputs):
                custom_input = custom_inputs[self.index]
                self.report({'INFO'}, f"Updated custom input: {custom_input.name}")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Invalid custom input index")
                return {'CANCELLED'}
        except Exception as e:
            logger.error(f"Error editing custom input: {e}")
            self.report({'ERROR'}, f"Failed to edit custom input: {e}")
            return {'CANCELLED'}

class CLE_OT_RemoveCustomInput(bpy.types.Operator):
    """
    Operator to remove a custom input.
    """
    bl_idname = "wm.cle_remove_custom_input"
    bl_label = "Remove Custom Input"
    bl_description = "Remove a custom controller input mapping"
    
    index: IntProperty(
        name="Index",
        description="Index of the custom input to remove",
        default=0
    )
    
    def execute(self, context):
        """Remove the custom input."""
        try:
            custom_inputs = getattr(context.scene, 'cle_custom_inputs', [])
            if self.index < len(custom_inputs):
                custom_input = custom_inputs[self.index]
                name = custom_input.name
                custom_inputs.remove(self.index)
                self.report({'INFO'}, f"Removed custom input: {name}")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Invalid custom input index")
                return {'CANCELLED'}
        except Exception as e:
            logger.error(f"Error removing custom input: {e}")
            self.report({'ERROR'}, f"Failed to remove custom input: {e}")
            return {'CANCELLED'}

def register_custom_input_classes():
    """Register all custom input related classes."""
    bpy.utils.register_class(CLE_CustomInput)
    bpy.utils.register_class(CLE_OT_AddCustomInput)
    bpy.utils.register_class(CLE_OT_EditCustomInput)
    bpy.utils.register_class(CLE_OT_RemoveCustomInput)

def unregister_custom_input_classes():
    """Unregister all custom input related classes."""
    bpy.utils.unregister_class(CLE_OT_RemoveCustomInput)
    bpy.utils.unregister_class(CLE_OT_EditCustomInput)
    bpy.utils.unregister_class(CLE_OT_AddCustomInput)
    bpy.utils.unregister_class(CLE_CustomInput)