import c4d
from c4d import gui

def RunSanityCheck( dialog ):

    dialog.SetString( dialog.DepartmentBoxID, "The Best Department!" )
    dialog.SetLong( dialog.PriorityBoxID, 33 )
    dialog.SetLong( dialog.ConcurrentTasksBoxID, 2 )

    gui.MessageDialog( "This is a custom sanity check!" )

    return True
