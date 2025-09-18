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

classes = (
    recording.CLE_OT_LiveControllerInputs,
    recording.CLE_OT_RecordControllerInputs,
    nodegroups.CLE_OT_CreateNodegroup,
    ui.CLE_PT_Main,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.cle_record_modal_running = bpy.props.BoolProperty(default=False)
    bpy.types.Scene.cle_live_modal_running = bpy.props.BoolProperty(default=False)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
