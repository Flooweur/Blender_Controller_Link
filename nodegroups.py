"""
Node group creation and management module for Blender Controller Link Extended.
Handles geometry node group creation with improved error handling.
"""

import bpy
import logging
from typing import Optional, Set
from .controller import get_reader

# Set up logging
logger = logging.getLogger(__name__)

class NodeGroupError(Exception):
    """Custom exception for node group related errors."""
    pass

def get_controller_properties(reader_object: bpy.types.Object) -> Set[str]:
    """
    Extract all controller-related properties from the reader object.
    
    Scans the CLE_reader object's custom properties and identifies those
    that represent controller inputs (prefixed with 'controller_') and
    have appropriate data types for use in geometry nodes.
    
    Args:
        reader_object: The CLE_reader object containing controller data
        
    Returns:
        Set[str]: Set of controller property names suitable for node outputs
    """
    """
    Get all controller properties from the reader object.
    
    Args:
        reader_object: The CLE_reader object containing controller data
        
    Returns:
        Set[str]: Set of controller property names
    """
        try:
            # Validate input object
            if not reader_object:
                return set()
            
        # Filter properties: only controller inputs with numeric/boolean values
        return {
            prop_name for prop_name, value in reader_object.items()
            if prop_name.startswith("controller_") and isinstance(value, (float, int, bool))
        }
    except Exception as e:
        logger.error(f"Error getting controller properties: {e}")
        return set()

def get_existing_outputs(nodegroup: bpy.types.GeometryNodeTree) -> Set[str]:
    """
    Get the names of all existing output sockets in a node group.
    
    Examines the node group's interface to find all output sockets,
    which is used to determine if the node group needs to be rebuilt
    when controller properties change.
    
    Args:
        nodegroup: The geometry node group to examine
        
    Returns:
        Set[str]: Set of existing output socket names
    """
    """
    Get existing output socket names from a node group.
    
    Args:
        nodegroup: The geometry node group
        
    Returns:
        Set[str]: Set of existing output socket names
    """
        try:
            # Validate node group and interface
            if not nodegroup or not nodegroup.interface:
                return set()
            
        # Extract names of all output sockets
        return {
            socket.name for socket in nodegroup.interface.items_tree
            if socket.in_out == 'OUTPUT'
        }
    except Exception as e:
        logger.error(f"Error getting existing outputs: {e}")
        return set()

def create_output_socket(nodegroup: bpy.types.GeometryNodeTree, prop_name: str) -> bool:
    """
    Create an output socket in the node group for a controller property.
    
    Adds a new float output socket to the node group interface if it doesn't
    already exist. This socket will be used to expose the controller property
    value to other nodes in the geometry node tree.
    
    Args:
        nodegroup: The geometry node group to modify
        prop_name: Name of the controller property
        
    Returns:
        bool: True if socket was created successfully, False on error
    """
    """
    Create an output socket for a controller property.
    
    Args:
        nodegroup: The geometry node group
        prop_name: Name of the controller property
        
    Returns:
        bool: True if successful, False otherwise
    """
        try:
            # Validate inputs
            if not nodegroup or not nodegroup.interface:
                logger.error("Invalid nodegroup or interface")
                return False
            
            # Create output interface socket if it doesn't exist
            if not nodegroup.interface.items_tree.get(prop_name):
                nodegroup.interface.new_socket(prop_name, in_out="OUTPUT", socket_type="NodeSocketFloat")
                logger.debug(f"Created output socket: {prop_name}")
                return True
            
        return True
        
    except Exception as e:
        logger.error(f"Error creating output socket for {prop_name}: {e}")
        return False

def setup_driver(output_node: bpy.types.Node, prop_name: str, reader_object: bpy.types.Object) -> bool:
    """
    Set up a driver to connect a controller property to a node output socket.
    
    Creates or updates a Blender driver that reads the controller property
    value from the CLE_reader object and feeds it to the node output socket.
    This enables real-time updates of geometry based on controller input.
    
    The driver uses a simple 'var' expression where 'var' is linked to
    the controller property on the reader object.
    
    Args:
        output_node: The group output node containing the socket
        prop_name: Name of the controller property
        reader_object: The CLE_reader object containing the property
        
    Returns:
        bool: True if driver was set up successfully, False on error
    """
    """
    Set up a driver for a node output socket.
    
    Args:
        output_node: The group output node
        prop_name: Name of the controller property
        reader_object: The CLE_reader object
        
    Returns:
        bool: True if successful, False otherwise
    """
        try:
            # Verify the socket exists on the output node
            if prop_name not in output_node.inputs:
                logger.warning(f"Property {prop_name} not found in output node inputs")
                return False

        output_socket = output_node.inputs[prop_name]

        # Set up or reuse existing driver
        fcurve = None
        try:
            # Try to create a new driver
            fcurve = output_socket.driver_add('default_value')
        except RuntimeError:
            # Driver might already exist - try to find it
            if output_socket.animation_data:
                fcurve = next(
                    (fc for fc in output_socket.animation_data.drivers if fc.data_path == 'default_value'),
                    None
                )

        if not fcurve:
            logger.warning(f"Could not create or find driver for {prop_name}")
            return False

        # Configure driver to use scripted expression
        fcurve.driver.type = 'SCRIPTED'
        driver = fcurve.driver

        # Set up driver variable (avoid duplicates)
        existing_var = next((v for v in driver.variables if v.name == 'var'), None)
        if not existing_var:
            # Create new variable pointing to controller property
            var = driver.variables.new()
            var.name = 'var'
            var.type = 'SINGLE_PROP'
            var.targets[0].id_type = 'OBJECT'
            var.targets[0].id = reader_object
            var.targets[0].data_path = f'["{prop_name}"]'
            logger.debug(f"Created new driver variable for {prop_name}")
        else:
            # Update existing variable to ensure it points to correct property
            var = existing_var
            tgt = var.targets[0]
            tgt.id_type = 'OBJECT'
            tgt.id = reader_object
            tgt.data_path = f'["{prop_name}"]'
            logger.debug(f"Updated existing driver variable for {prop_name}")

        driver.expression = 'var'
        return True
        
    except Exception as e:
        logger.error(f"Error setting up driver for {prop_name}: {e}")
        return False

def find_or_create_output_node(nodegroup: bpy.types.GeometryNodeTree) -> Optional[bpy.types.Node]:
    """
    Find the existing group output node or create a new one.
    
    Every geometry node group needs a Group Output node to expose values
    to the outside. This function ensures one exists and returns it.
    
    Args:
        nodegroup: The geometry node group
        
    Returns:
        Optional[bpy.types.Node]: The group output node, or None if creation failed
    """
    """
    Find existing or create new group output node.
    
    Args:
        nodegroup: The geometry node group
        
    Returns:
        Optional[bpy.types.Node]: The group output node or None if failed
    """
        try:
            # Search for existing Group Output node
            output_node = next((n for n in nodegroup.nodes if n.type == 'GROUP_OUTPUT'), None)
        
        if not output_node:
            # No output node exists - create one
            output_node = nodegroup.nodes.new('NodeGroupOutput')
            output_node.location = (200, 0)  # Position it to the right
            logger.info("Created new group output node")
        
        return output_node
        
    except Exception as e:
        logger.error(f"Error finding/creating output node: {e}")
        return None

class CLE_OT_CreateNodegroup(bpy.types.Operator):
    """
    Operator to create or update a geometry node group with controller inputs.
    
    This operator creates a special geometry node group called 'CLE_ControllerInputs'
    that exposes all controller properties as output sockets. This makes it easy
    to use controller inputs in geometry node setups by simply adding this node
    group to any geometry node tree.
    
    The operator:
    - Scans for available controller properties
    - Creates or updates the node group as needed
    - Sets up drivers to connect properties to outputs
    - Handles errors gracefully with user feedback
    
    The resulting node group can be added to any geometry node tree and will
    automatically provide real-time controller input values.
    """
    bl_idname = "wm.cle_create_nodegroup"
    bl_label = "Create Controller Nodegroup"
    bl_description = "Create or update a geometry node group with controller inputs"

    def execute(self, context):
        """
        Execute the node group creation/update process.
        
        This is the main method that orchestrates the entire node group
        creation process. It handles all the steps from property detection
        to driver setup, with comprehensive error handling and user feedback.
        
        Args:
            context: Blender context
            
        Returns:
            set: Blender operator return status
                - {'FINISHED'}: Node group created/updated successfully
                - {'CANCELLED'}: Operation failed or was cancelled
        """
        try:
            # Get the controller data storage object
            reader = get_reader()
            if not reader:
                self.report({'WARNING'}, "No controller reader object found")
                return {'CANCELLED'}

            # Define node group name and try to get existing group
            group_name = "CLE_ControllerInputs"
            nodegroup = bpy.data.node_groups.get(group_name)

            # Scan reader object for controller properties
            desired_outputs = get_controller_properties(reader)
            
            if not desired_outputs:
                self.report({'WARNING'}, "No controller properties found")
                return {'CANCELLED'}

            # Determine if node group needs to be rebuilt
            rebuild_needed = False
            if nodegroup:
                # Compare existing outputs with current controller properties
                current_outputs = get_existing_outputs(nodegroup)
                if current_outputs != desired_outputs:
                    rebuild_needed = True
                    logger.info("Node group outputs out of sync, rebuilding")
            else:
                # No existing node group found
                rebuild_needed = True
                logger.info("Node group doesn't exist, creating new one")

            # Rebuild node group if outputs don't match current properties
            if rebuild_needed:
                if nodegroup:
                    try:
                        # Remove old node group to start fresh
                        bpy.data.node_groups.remove(nodegroup)
                        logger.info("Removed old node group")
                    except Exception as e:
                        logger.warning(f"Error removing old node group: {e}")
                
                try:
                    # Create new geometry node group
                    nodegroup = bpy.data.node_groups.new(group_name, 'GeometryNodeTree')
                    logger.info(f"Created new node group: {group_name}")
                except Exception as e:
                    logger.error(f"Error creating new node group: {e}")
                    self.report({'ERROR'}, f"Failed to create node group: {e}")
                    return {'CANCELLED'}

            # Find or create group output node
            output_node = find_or_create_output_node(nodegroup)
            if not output_node:
                self.report({'ERROR'}, "Failed to create group output node")
                return {'CANCELLED'}

            # Create sockets and drivers for each controller property
            success_count = 0
            for prop_name in desired_outputs:
                try:
                    # Step 1: Create output socket in node group interface
                    if create_output_socket(nodegroup, prop_name):
                        # Step 2: Set up driver to connect property to socket
                        if setup_driver(output_node, prop_name, reader):
                            success_count += 1
                        else:
                            logger.warning(f"Failed to setup driver for {prop_name}")
                    else:
                        logger.warning(f"Failed to create output socket for {prop_name}")
                        
                except Exception as e:
                    logger.error(f"Error processing property {prop_name}: {e}")
                    continue

            # Report results to user
            if success_count > 0:
                self.report({'INFO'}, f"Node group '{group_name}' ready with {success_count} controller outputs.")
                logger.info(f"Successfully created node group with {success_count}/{len(desired_outputs)} outputs")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "Failed to create any controller outputs")
                return {'CANCELLED'}
                
        except Exception as e:
            logger.error(f"Error in create nodegroup operator: {e}")
            self.report({'ERROR'}, f"Failed to create node group: {e}")
            return {'CANCELLED'}
