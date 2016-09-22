import os
import sys
import subprocess
import re
import traceback
import string

try:
    import ConfigParser
except:
    print( "Could not load ConfigParser module, sticky settings will not be loaded/saved" )

import c4d
from c4d import documents
from c4d import gui
from c4d import plugins

useTakes = False
try:
    from c4d.modules import takesystem
    useTakes = True
except:
    print( "Could not load takesystem module, modules will not be used." )
    
## The submission dialog class.
class SubmitC4DToDeadlineDialog (gui.GeDialog):
    DeadlineHome = ""
    DeadlineSettings = ""
    DeadlineTemp = ""
    DeadlineRepositoryRoot = ""
    ConfigFile = ""
    SanityCheckFile = ""
    
    MaximumPriority = 100
    Pools = []
    SecondaryPools = []
    Groups = []
    OnComplete = []
    Builds = []
    
    ShotgunJobSettings = {}
    FTrackJobSettings = {}
    PulledFTrackJobSettings = {}
    NimJobSettings = {}
    
    Formats = []
    Resolutions = []
    FrameRates = []
    Restrictions = []

    CurrentCodecs = []
    CurrentFrameRates = []
    FormatsDict = {}
    ResolutionsDict = {}
    CodecsDict = {}
    RestrictionsDict = {}
    
    integrationType = 0 #0 = Shotgun 1 = FTrack 2 = NIM
    
    LabelWidth = 200
    TextBoxWidth = 600
    ComboBoxWidth = 180
    RangeBoxWidth = 190
    
    SliderLabelWidth = 180
    
    LabelID = 1000
    NameBoxID = 10
    CommentBoxID = 20
    DepartmentBoxID = 30
    PoolBoxID = 40
    SecondaryPoolBoxID = 45
    GroupBoxID = 50
    PriorityBoxID = 60
    AutoTimeoutBoxID = 65
    TaskTimeoutBoxID = 70
    ConcurrentTasksBoxID = 80
    LimitConcurrentTasksBoxID = 85
    MachineLimitBoxID = 90
    IsBlacklistBoxID = 94
    MachineListBoxID=  96
    MachineListButtonID = 98
    LimitGroupsBoxID = 100
    LimitGroupsButtonID = 110
    DependenciesBoxID = 120
    DependenciesButtonID = 130
    OnCompleteBoxID = 140
    SubmitSuspendedBoxID = 150
    FramesBoxID = 160
    ChunkSizeBoxID = 170
    ThreadsBoxID = 180

    TakesBoxID = 191
    IncludeMainBoxID = 192

    BuildBoxID = 190
    LocalRenderingBoxID = 195
    SubmitSceneBoxID = 200
    ExportProjectBoxID = 205
    
    ConnectToIntegrationButtonID = 210
    UseIntegrationBoxID = 220
    IntegrationVersionBoxID = 225
    IntegrationInfoBoxID = 230
    IntegrationDescriptionBoxID = 235
    
    SubmitDraftJobBoxID = 240
    UploadDraftToShotgunBoxID = 250
    DraftTemplateBoxID = 260
    DraftTemplateButtonID = 270
    DraftUserBoxID = 280
    DraftEntityBoxID = 290
    DraftVersionBoxID = 300
    DraftUseShotgunDataButtonID = 310
    DraftExtraArgsBoxID = 320
    
    UseQuickDraftBoxID = 321
    QuickDraftFormatID = 322
    QuickDraftCodecID = 323
    QuickDraftResolutionID = 324
    QuickDraftQualityID = 325
    QuickDraftFrameRateID = 326
    
    IntegrationTypeBoxID = 330
    uploadLayout = 360
    UploadMovieBoxID = 340
    UploadFilmStripBoxID = 350
    
    SubmitButtonID = 910
    CancelButtonID = 920
    
    def __init__( self ):
        c4d.StatusSetBar( 15 )
        
        stdout = None
        
        # Get the current user Deadline home directory, which we'll use to store settings and temp files.
        print( "Getting Deadline home folder" )
        self.DeadlineHome = CallDeadlineCommand( ["-GetCurrentUserHomeDirectory",] )
        self.DeadlineHome = self.DeadlineHome.replace( "\n", "" ).replace( "\r", "" )
        
        self.DeadlineSettings = self.DeadlineHome + "/settings"
        self.DeadlineTemp = self.DeadlineHome + "/temp"
        
        c4d.StatusSetBar( 30 )
        
        # Get the maximum priority.
        print( "Getting maximum priority" )
        try:
            output = CallDeadlineCommand( ["-getmaximumpriority",] )
            self.MaximumPriority = int(output)
        except:
            self.MaximumPriority = 100
        
        c4d.StatusSetBar( 45 )
        
        # Get the pools.
        print( "Loading pools" )
        output = CallDeadlineCommand( ["-pools",] )
        
        self.Pools = []
        self.SecondaryPools = []
        for line in output.splitlines():
            currPool = line.replace( "\n", "" )
            self.Pools.append( currPool )
            self.SecondaryPools.append( currPool ) 
            
        if len(self.Pools) == 0:
            self.Pools.append( "none" )
            self.SecondaryPools.append( "none" ) 
            
        # Need to have a space, since empty strings don't seem to show up.
        self.SecondaryPools.insert( 0, " " ) 
        
        c4d.StatusSetBar( 60 )
        
        # Get the groups.
        print( "Loading groups" )
        output = CallDeadlineCommand( ["-groups",] )
        
        self.Groups = []
        for line in output.splitlines():
            self.Groups.append( line.replace( "\n", "" ) )
        
        if len(self.Groups) == 0:
            self.Groups.append( "none" )
            
        c4d.StatusSetBar( 75 )
        
        # Get the repo root.
        print( "Getting Repository root" )
        self.DeadlineRepositoryRoot = CallDeadlineCommand( ["-GetRepositoryRoot",] )
        self.DeadlineRepositoryRoot = self.DeadlineRepositoryRoot.replace( "\n", "" ).replace( "\r", "" )
        
        c4d.StatusSetBar( 100 )
        
        # Set On Job Complete settings.
        self.OnComplete = []
        self.OnComplete.append( "Archive" )
        self.OnComplete.append( "Delete" )
        self.OnComplete.append( "Nothing" )
        
        # Set Build settings.
        self.Builds = []
        self.Builds.append( "None" )
        self.Builds.append( "32bit" )
        self.Builds.append( "64bit" )
        
        self.Takes = []
        takesCanbeMarked = True
        if useTakes:
            # Set Takes setting
            doc = documents.GetActiveDocument()
            takeData = doc.GetTakeData()
            take = takeData.GetMainTake()
            #Takes were able to be marked starting in C4D R17 SP1 so this will make sure it doesn't break in 
            
            try:
                take.IsChecked()
            except:
                takesCanbeMarked = False
                
            self.CurrentTake = takeData.GetCurrentTake().GetName()
            while take:
                name = take.GetName() # this is the take name
                self.Takes.append( name )
                take = GetNextObject(take)
        else:
            self.CurrentTake = " "
        
        if takesCanbeMarked:
            self.Takes.insert( 0, "Marked" )
        
        if len(self.Takes) >1:
            self.Takes.insert( 0, "All" )
            
        self.Takes.insert( 0, " " )
            

        c4d.StatusClear()
    
    def GetLabelID( self ):
        self.LabelID = self.LabelID + 1
        return self.LabelID
    
    def StartGroup( self, label ):
        self.GroupBegin( self.GetLabelID(), 0, 0, 20, label, 0 )
        self.GroupBorder( c4d.BORDER_THIN_IN )
        self.GroupBorderSpace( 4, 4, 4, 4 )
    
    def EndGroup( self ):
        self.GroupEnd()
    
    def AddTextBoxGroup( self, id, label ):
        self.GroupBegin( self.GetLabelID(), 0, 2, 1, "", 0 )
        self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth, 0, label, 0 )
        self.AddEditText( id, 0, self.TextBoxWidth, 0 )
        self.GroupEnd()
    
    def AddComboBoxGroup( self, id, label, checkboxID=-1, checkboxLabel="" ):
        self.GroupBegin( self.GetLabelID(), 0, 3, 1, "", 0 )
        self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth, 0, label, 0 )
        self.AddComboBox( id, 0, self.ComboBoxWidth, 0 )
        if checkboxID >= 0 and checkboxLabel != "":
            self.AddCheckbox( checkboxID, 0, self.LabelWidth + self.ComboBoxWidth + 12, 0, checkboxLabel )
        elif checkboxID > -2:
            self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth + self.ComboBoxWidth + 12, 0, "", 0 )
        self.GroupEnd()
    
    def AddRangeBoxGroup( self, id, label, min, max, inc, checkboxID=-1, checkboxLabel="" ):
        self.GroupBegin( self.GetLabelID(), 0, 3, 1, "", 0 )
        self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth, 0, label, 0 )
        self.AddEditNumberArrows( id, 0, self.RangeBoxWidth, 0 )
        if checkboxID >= 0 and checkboxLabel != "":
            self.AddCheckbox( checkboxID, 0, self.LabelWidth + self.ComboBoxWidth + 12, 0, checkboxLabel )
        else:
            self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth + self.RangeBoxWidth + 4, 0, "", 0 )
        self.SetLong( id, min, min, max, inc )
        self.GroupEnd()
    
    def AddSelectionBoxGroup( self, id, label, buttonID ):
        self.GroupBegin( self.GetLabelID(), 0, 3, 1, "", 0 )
        self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth, 0, label, 0 )
        self.AddEditText( id, 0, self.TextBoxWidth - 56, 0 )
        self.AddButton( buttonID, 0, 8, 0, "..." )
        self.GroupEnd()
    
    def AddCheckboxGroup( self, checkboxID, checkboxLabel, textID, buttonID ):
        self.GroupBegin( self.GetLabelID(), 0, 3, 1, "", 0 )
        self.AddCheckbox( checkboxID, 0, self.LabelWidth, 0, checkboxLabel )
        self.AddEditText( textID, 0, self.TextBoxWidth - 56, 0 )
        self.AddButton( buttonID, 0, 8, 0, "..." )
        self.GroupEnd()
    
    ## This is called when the dialog is initialized.
    def CreateLayout( self ):
        self.SetTitle( "Submit To Deadline" )
        
        self.TabGroupBegin( self.GetLabelID(), 0 )
        #General Options Tab
        self.GroupBegin( self.GetLabelID(), 0, 0, 20, "General Options", 0 )
        self.GroupBorderNoTitle( c4d.BORDER_NONE )
        
        self.StartGroup( "Job Description" )
        self.AddTextBoxGroup( self.NameBoxID, "Job Name" )
        self.AddTextBoxGroup( self.CommentBoxID, "Comment" )
        self.AddTextBoxGroup( self.DepartmentBoxID, "Department" )
        self.EndGroup()
        
        self.StartGroup( "Job Options" )
        self.AddComboBoxGroup( self.PoolBoxID, "Pool" )
        self.AddComboBoxGroup( self.SecondaryPoolBoxID, "Secondary Pool" )
        self.AddComboBoxGroup( self.GroupBoxID, "Group" )
        self.AddRangeBoxGroup( self.PriorityBoxID, "Priority", 0, 100, 1 )
        self.AddRangeBoxGroup( self.TaskTimeoutBoxID, "Task Timeout", 0, 999999, 1, self.AutoTimeoutBoxID, "Enable Auto Task Timeout" )
        self.AddRangeBoxGroup( self.ConcurrentTasksBoxID, "Concurrent Tasks", 1, 16, 1, self.LimitConcurrentTasksBoxID, "Limit Tasks To Slave's Task Limit" )
        self.AddRangeBoxGroup( self.MachineLimitBoxID, "Machine Limit", 0, 999999, 1, self.IsBlacklistBoxID, "Machine List is a Blacklist" )
        self.AddSelectionBoxGroup( self.MachineListBoxID, "Machine List", self.MachineListButtonID )
        self.AddSelectionBoxGroup( self.LimitGroupsBoxID, "Limit Groups", self.LimitGroupsButtonID )
        self.AddSelectionBoxGroup( self.DependenciesBoxID, "Dependencies", self.DependenciesButtonID )
        self.AddComboBoxGroup( self.OnCompleteBoxID, "On Job Complete", self.SubmitSuspendedBoxID, "Submit Job As Suspended" )
        self.EndGroup()
        
        self.StartGroup( "Cinema 4D Options" )

        self.AddComboBoxGroup( self.TakesBoxID, "Take List", self.IncludeMainBoxID, "Include Main take in All takes" )
        #self.AddCheckbox( self.IncludeMainBoxID, 0, self.LabelWidth+self.ComboBoxWidth + 12, 0, "Include Main take in All takes" )

        self.AddTextBoxGroup( self.FramesBoxID, "Frame List" )
        #self.AddRangeBoxGroup( self.ChunkSizeBoxID, "Frames Per Task", 1, 999999, 1 )
        #self.AddRangeBoxGroup( self.ThreadsBoxID, "Threads To Use", 0, 16, 1 )
        #self.AddComboBoxGroup( self.BuildBoxID, "Build To Force", self.SubmitSceneBoxID, "Submit Cinema 4D Scene File" )
        
        self.AddRangeBoxGroup( self.ChunkSizeBoxID, "Frames Per Task", 1, 999999, 1, self.SubmitSceneBoxID, "Submit Cinema 4D Scene File" )
        self.AddRangeBoxGroup( self.ThreadsBoxID, "Threads To Use", 0, 256, 1, self.ExportProjectBoxID, "Export Project Before Submission" )
        self.AddComboBoxGroup( self.BuildBoxID, "Build To Force", self.LocalRenderingBoxID, "Enable Local Rendering" )
        
        self.EndGroup()
        
        self.GroupEnd() #General Options Tab
        
        #Shotgun/Draft Tab
        self.GroupBegin( self.GetLabelID(), c4d.BFV_TOP, 0, 20, "Integration", 0 )
        self.GroupBorderNoTitle( c4d.BORDER_NONE )
        
        self.StartGroup( "Project Management" )
        self.GroupBegin( self.GetLabelID(), 0, 3, 1, "", 0 )
        #self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth, 0, "Project Management", 0 )
        #self.AddComboBox( self.IntegrationTypeBoxID, 0, self.ComboBoxWidth, 0 )
        self.AddComboBoxGroup( self.IntegrationTypeBoxID, "Project Management" )
        self.GroupEnd()
        
        self.GroupBegin( self.GetLabelID(), 0, 3, 1, "", 0 )
        self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth, 0, "", 0 )
        #self.AddComboBox( self.IntegrationTypeBoxID, 0, self.ComboBoxWidth, 0 )
        self.AddButton( self.ConnectToIntegrationButtonID, 0, self.ComboBoxWidth, 0, "Connect..." )
        self.AddCheckbox( self.UseIntegrationBoxID, 0, self.LabelWidth+self.ComboBoxWidth + 12, 0, "Create new version" )
        self.Enable( self.UseIntegrationBoxID, False )
        self.GroupEnd()        
        self.AddTextBoxGroup( self.IntegrationVersionBoxID, "Version Name" )
        self.AddTextBoxGroup( self.IntegrationDescriptionBoxID, "Description" )
        
        self.GroupBegin( self.GetLabelID(), c4d.BFV_TOP, 2, 1, "", 0 )
        self.AddStaticText( self.GetLabelID(), c4d.BFV_TOP, self.LabelWidth + 3, 0, "Selected Entity Info", 0 )
        self.AddMultiLineEditText( self.IntegrationInfoBoxID, c4d.BFV_TOP, self.TextBoxWidth + 20, 95 )
        self.Enable( self.IntegrationInfoBoxID, False )
        self.GroupEnd()
        
        
        self.GroupBegin( self.uploadLayout, 0, 3, 1, "", 0 )
        self.AddStaticText( self.uploadLayout+1, 0, self.LabelWidth, 0, "Draft Options", 0 )
        self.AddCheckbox( self.UploadMovieBoxID, 0, self.LabelWidth+ + 12, 0, "Create/Upload Movie" )
        self.Enable( self.UploadMovieBoxID, False )
        self.AddCheckbox( self.UploadFilmStripBoxID, 0, self.LabelWidth + self.ComboBoxWidth + 12, 0, "Create/Upload Film Strip" )
        self.Enable( self.UploadFilmStripBoxID, False )
        self.GroupEnd()
        
        self.EndGroup() #Shotgun group
        
        self.StartGroup( "Draft" )
        self.GroupBegin( self.GetLabelID(), c4d.BFH_LEFT, 2, 1, "", 0 )
        self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth, 0, "", 0 )
        self.AddCheckbox( self.SubmitDraftJobBoxID, 0, 320, 0, "Submit Draft Job On Completion" )
        self.EndGroup()
        
        self.GroupBegin( self.GetLabelID(), c4d.BFH_LEFT, 3, 1, "", 0 )
        self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth, 0, "", 0 )
        self.AddCheckbox( self.UseQuickDraftBoxID, 0, 280, 0, "Use Quick Draft" )
        self.AddCheckbox( self.UploadDraftToShotgunBoxID, 0, 320, 0, "Upload Draft Results To Shotgun" )
        self.EndGroup()
        
        self.AddComboBoxGroup( self.QuickDraftFormatID, "Format" )
        self.AddComboBoxGroup( self.QuickDraftCodecID, "Compression" )
        self.AddComboBoxGroup( self.QuickDraftResolutionID, "Resolution" )
        self.AddRangeBoxGroup( self.QuickDraftQualityID, "Quality", 0, 100, 1 )
        self.AddComboBoxGroup( self.QuickDraftFrameRateID, "Frame Rate" )
                
        self.AddSelectionBoxGroup( self.DraftTemplateBoxID, "Draft Template", self.DraftTemplateButtonID )
        self.AddTextBoxGroup( self.DraftUserBoxID, "User Name" )
        self.AddTextBoxGroup( self.DraftEntityBoxID, "Entity Name" )
        self.AddTextBoxGroup( self.DraftVersionBoxID, "Version Name" )
        self.AddTextBoxGroup( self.DraftExtraArgsBoxID, "Additional Args" )
        
        self.GroupBegin( self.GetLabelID(), c4d.BFH_LEFT, 2, 1, "", 0 )
        self.AddStaticText( self.GetLabelID(), 0, self.LabelWidth, 0, "", 0 )
        self.AddButton( self.DraftUseShotgunDataButtonID, 0, self.ComboBoxWidth, 0, "Use Shotgun Data" )
        self.EndGroup()
        self.EndGroup() #Draft group
        
        #Updates enabled status of the draft controls
        
        self.ReadInDraftOptions()
        
        self.Command( self.SubmitDraftJobBoxID, None )
        self.Command( self.UseIntegrationBoxID, None )
        
        self.GroupEnd() #Shotgun/Draft tab
        self.GroupEnd() #Tab group
        
        self.GroupBegin( self.GetLabelID(), 0, 2, 1, "", 0 )
        self.AddButton( self.SubmitButtonID, 0, 100, 0, "Submit" )
        self.AddButton( self.CancelButtonID, 0, 100, 0, "Cancel" )
        self.GroupEnd()
        
        return True
    
    ## This is called after the dialog has been initialized.
    def InitValues( self ):
        scene = documents.GetActiveDocument()
        sceneName = scene.GetDocumentName()
        frameRate = scene.GetFps()
        
        startFrame = 0
        endFrame = 0
        stepFrame = 0
        
        renderData = scene.GetActiveRenderData().GetData()
        frameMode = renderData.GetLong( c4d.RDATA_FRAMESEQUENCE )
        if frameMode == c4d.RDATA_FRAMESEQUENCE_MANUAL:
            startFrame = renderData.GetTime( c4d.RDATA_FRAMEFROM ).GetFrame( frameRate )
            endFrame = renderData.GetTime( c4d.RDATA_FRAMETO ).GetFrame( frameRate )
            stepFrame = renderData.GetLong( c4d.RDATA_FRAMESTEP )
        elif frameMode == c4d.RDATA_FRAMESEQUENCE_CURRENTFRAME:
            startFrame = scene.GetTime().GetFrame( frameRate )
            endFrame = startFrame
            stepFrame = 1
        elif frameMode == c4d.RDATA_FRAMESEQUENCE_ALLFRAMES:
            startFrame = scene.GetMinTime().GetFrame( frameRate )
            endFrame = scene.GetMaxTime().GetFrame( frameRate )
            stepFrame = renderData.GetLong( c4d.RDATA_FRAMESTEP )
        elif frameMode == c4d.RDATA_FRAMESEQUENCE_PREVIEWRANGE:
            startFrame = scene.GetLoopMinTime().GetFrame( frameRate )
            endFrame = scene.GetLoopMaxTime().GetFrame( frameRate )
            stepFrame = renderData.GetLong( c4d.RDATA_FRAMESTEP )
        
        frameList = str(startFrame)
        if startFrame != endFrame:
            frameList = frameList + "-" + str(endFrame)
        if stepFrame > 1:
            frameList = frameList + "x" + str(stepFrame)
        
        initName = sceneName
        initComment = ""
        initDepartment = ""
        
        initPool = "none"
        initSecondaryPool = " " # Needs to have a space
        initGroup = "none"
        initPriority = 50
        initMachineLimit = 0
        initTaskTimeout = 0
        initAutoTaskTimeout = False
        initConcurrentTasks = 1
        initLimitConcurrentTasks = True
        initIsBlacklist = False
        initMachineList = ""
        initLimitGroups = ""
        initDependencies = ""
        initOnComplete = "Nothing"
        initSubmitSuspended = False
        
        initTakes = "None"
        initIncludeMainTake = False
        
        initFrames = frameList
        initChunkSize = 1
        initThreads = 0
        initBuild = "None"
        initSubmitScene = False
        initExportProject = False
        initLocalRendering = False
        
        initSubmitDraftJob = False
        initUseQuickDraft = True
        
        initDraftTemplate = ""
        initDraftUser = ""
        initDraftEntity = ""
        initDraftVersion = ""
        initDraftExtraArgs = ""
        
        initIntegration = "Shotgun"
        
        initQuickDraftFormat = "JPEG (jpg)"
        initQuickDraftResolution = "Full"
        initQuickDraftCodec = "mjpeg"
        initQuickDraftQuality = 85
        initQuickDraftFrameRate = "24"
        
        # Read in sticky settings
        self.ConfigFile = self.DeadlineSettings + "/c4d_py_submission.ini"
        try:
            if os.path.isfile( self.ConfigFile ):
                config = ConfigParser.ConfigParser()
                config.read( self.ConfigFile )
                
                if config.has_section( "Sticky" ):
                    if config.has_option( "Sticky", "Department" ):
                        initDepartment = config.get( "Sticky", "Department" )
                    if config.has_option( "Sticky", "Pool" ):
                        initPool = config.get( "Sticky", "Pool" )
                    if config.has_option( "Sticky", "SecondaryPool" ):
                        initSecondaryPool = config.get( "Sticky", "SecondaryPool" )
                    if config.has_option( "Sticky", "Group" ):
                        initGroup = config.get( "Sticky", "Group" )
                    if config.has_option( "Sticky", "Priority" ):
                        initPriority = config.getint( "Sticky", "Priority" )
                    if config.has_option( "Sticky", "MachineLimit" ):
                        initMachineLimit = config.getint( "Sticky", "MachineLimit" )
                    if config.has_option( "Sticky", "LimitGroups" ):
                        initLimitGroups = config.get( "Sticky", "LimitGroups" )
                    if config.has_option( "Sticky", "IsBlacklist" ):
                        initIsBlacklist = config.getboolean( "Sticky", "IsBlacklist" )
                    if config.has_option( "Sticky", "MachineList" ):
                        initMachineList = config.get( "Sticky", "MachineList" )
                    if config.has_option( "Sticky", "SubmitSuspended" ):
                        initSubmitSuspended = config.getboolean( "Sticky", "SubmitSuspended" )
                    if config.has_option( "Sticky", "ChunkSize" ):
                        initChunkSize = config.getint( "Sticky", "ChunkSize" )
                    if config.has_option( "Sticky", "Threads" ):
                        initThreads = config.getint( "Sticky", "Threads" )
                    if config.has_option( "Sticky", "Build" ):
                        initBuild = config.get( "Sticky", "Build" )
                    if config.has_option( "Sticky", "SubmitScene" ):
                        initSubmitScene = config.getboolean( "Sticky", "SubmitScene" )
                    if config.has_option( "Sticky", "SubmitDraftJob" ):
                        initSubmitDraftJob = config.getboolean( "Sticky", "SubmitDraftJob" )
                    if config.has_option( "Sticky", "UseQuickDraft" ):
                        initUseQuickDraft = config.getboolean( "Sticky", "UseQuickDraft" )
                    if config.has_option( "Sticky", "DraftTemplate" ):
                        initDraftTemplate = config.get( "Sticky", "DraftTemplate" )
                    if config.has_option( "Sticky", "DraftUser" ):
                        initDraftUser = config.get( "Sticky", "DraftUser" )
                    if config.has_option( "Sticky", "DraftEntity" ):
                        initDraftEntity = config.get( "Sticky", "DraftEntity" )
                    if config.has_option( "Sticky", "DraftVersion" ):
                        initDraftVersion = config.get( "Sticky", "DraftVersion" )
                    if config.has_option( "Sticky", "ExportProject" ):
                        initExportProject = config.getboolean( "Sticky", "ExportProject" )
                    if config.has_option( "Sticky", "LocalRendering" ):
                        initLocalRendering = config.getboolean( "Sticky", "LocalRendering" )
                    if config.has_option( "Sticky", "DraftExtraArgs" ):
                        initDraftExtraArgs = config.get( "Sticky", "DraftExtraArgs" )
                    if config.has_option( "Sticky", "Integration" ):
                        initIntegration = config.get( "Sticky", "Integration" )
                    
                    if config.has_option( "Sticky", "QuickDraftFormat" ):
                        initQuickDraftFormat = config.get( "Sticky", "QuickDraftFormat" )
                    if config.has_option( "Sticky", "QuickDraftResolution" ):
                        initQuickDraftResolution = config.get( "Sticky", "QuickDraftResolution" )
                    if config.has_option( "Sticky", "QuickDraftCodec" ):
                        initQuickDraftCodec = config.get( "Sticky", "QuickDraftCodec" )
                    if config.has_option( "Sticky", "QuickDraftQuality" ):
                        initQuickDraftQuality = int(config.get( "Sticky", "QuickDraftQuality" ))
                    if config.has_option( "Sticky", "QuickDraftFrameRate" ):
                        initQuickDraftFrameRate = config.get( "Sticky", "QuickDraftFrameRate" )
                        
                    if config.has_option( "Sticky", "IncludeMainTake" ):
                        initIncludeMainTake = config.getboolean( "Sticky", "IncludeMainTake" )
        except:
            print( "Could not read sticky settings" )
        
        if initPriority > self.MaximumPriority:
            initPriority = self.MaximumPriority / 2
        
        selectedFormat = 0
        for i in range( 0, len(self.Formats) ):
            self.AddChild( self.QuickDraftFormatID, i, self.Formats[ i ] )
            if initQuickDraftFormat == self.Formats[ i ]:
                selectedFormat = i
        
        selectedResolution = 0
        for i in range( 0, len(self.Resolutions) ):
            self.AddChild( self.QuickDraftResolutionID, i, self.Resolutions[ i ] )
            if initQuickDraftResolution == self.Resolutions[ i ]:
                selectedResolution = i
        
        currFormat = self.FormatsDict[self.Formats[selectedFormat]][0]
        self.CurrentCodecs = self.GetOptions(self.FormatsDict[self.Formats[selectedFormat]][0], "Codec", self.CodecsDict[currFormat])
        
        selectedCodec = 0
        for i in range( 0, len(self.CurrentCodecs) ):
            self.AddChild( self.QuickDraftCodecID, i, self.CurrentCodecs[ i ] )
            if initQuickDraftCodec == self.CurrentCodecs[ i ]:
                selectedCodec = i
        
        self.CurrentFrameRates = self.GetOptions( self.FormatsDict[self.Formats[selectedFormat]][0], "FrameRate", self.FrameRates )
        self.CurrentFrameRates = self.GetOptions( self.CurrentCodecs[ selectedCodec ], "FrameRate", self.CurrentFrameRates )
                
        selectedFrameRate = 0
        for i in range( 0, len(self.CurrentFrameRates) ):
            self.AddChild( self.QuickDraftFrameRateID, i, self.CurrentFrameRates[ i ] )
            if initQuickDraftFrameRate == self.CurrentFrameRates[ i ]:
                selectedFrameRate = i
        
        # Populate the combo boxes, and figure out the default selected index if necessary.
        selectedPoolID = 0
        for i in range( 0, len(self.Pools) ):
            self.AddChild( self.PoolBoxID, i, self.Pools[ i ] )
            if initPool == self.Pools[ i ]:
                selectedPoolID = i
        
        selectedSecondaryPoolID = 0
        for i in range( 0, len(self.SecondaryPools) ):
            self.AddChild( self.SecondaryPoolBoxID, i, self.SecondaryPools[ i ] )
            if initSecondaryPool == self.SecondaryPools[ i ]:
                selectedSecondaryPoolID = i
        
        selectedGroupID = 0
        for i in range( 0, len(self.Groups) ):
            self.AddChild( self.GroupBoxID, i, self.Groups[ i ] )
            if initGroup == self.Groups[ i ]:
                selectedGroupID = i
        
        selectedOnCompleteID = 0
        for i in range( 0, len(self.OnComplete) ):
            self.AddChild( self.OnCompleteBoxID, i, self.OnComplete[ i ] )
            if initOnComplete == self.OnComplete[ i ]:
                selectedOnCompleteID = i
        
        selectedBuildID = 0
        for i in range( 0, len(self.Builds) ):
            self.AddChild( self.BuildBoxID, i, self.Builds[ i ] )
            if initBuild == self.Builds[ i ]:
                selectedBuildID = i

        # Fill the take array
        selectedTakeID = 0
        for i in range( 0, len(self.Takes) ):
            self.AddChild( self.TakesBoxID, i, self.Takes[ i ] )
            if initTakes == self.Takes[ i ]:
                selectedTakeID = i

        # Find current take in list of all takes
        selectedTakeID = self.Takes.index( str( self.CurrentTake ) )
        self.Enable( self.TakesBoxID, useTakes )
        self.Enable( self.IncludeMainBoxID, useTakes )
        self.SetBool( self.IncludeMainBoxID, initIncludeMainTake )
        
        self.AddChild( self.IntegrationTypeBoxID, 0, "Shotgun" )
        if initIntegration == "FTrack":
            self.integrationType = 1
        self.AddChild( self.IntegrationTypeBoxID, 1, "FTrack" )
        if initIntegration == "NIM":
            self.integrationType = 2
        self.AddChild( self.IntegrationTypeBoxID, 2, "NIM" )
        
        # Set the default settings.
        self.SetString( self.NameBoxID, initName )
        self.SetString( self.CommentBoxID, initComment )
        self.SetString( self.DepartmentBoxID, initDepartment )
        
        self.SetLong( self.PoolBoxID, selectedPoolID )
        self.SetLong( self.SecondaryPoolBoxID, selectedSecondaryPoolID )
        self.SetLong( self.GroupBoxID, selectedGroupID )
        self.SetLong( self.PriorityBoxID, initPriority, 0, self.MaximumPriority, 1 )
        self.SetLong( self.MachineLimitBoxID, initMachineLimit )
        self.SetLong( self.TaskTimeoutBoxID, initTaskTimeout )
        self.SetBool( self.AutoTimeoutBoxID, initAutoTaskTimeout )
        self.SetLong( self.ConcurrentTasksBoxID, initConcurrentTasks )
        self.SetBool( self.LimitConcurrentTasksBoxID, initLimitConcurrentTasks )
        self.SetBool( self.IsBlacklistBoxID, initIsBlacklist )
        self.SetString( self.MachineListBoxID, initMachineList )
        self.SetString( self.LimitGroupsBoxID, initLimitGroups )
        self.SetString( self.DependenciesBoxID, initDependencies )
        self.SetLong( self.OnCompleteBoxID, selectedOnCompleteID )
        self.SetBool( self.SubmitSuspendedBoxID, initSubmitSuspended )

        self.SetLong( self.TakesBoxID, selectedTakeID )

        self.SetString( self.FramesBoxID, initFrames )
        self.SetLong( self.ChunkSizeBoxID, initChunkSize )
        self.SetLong( self.ThreadsBoxID, initThreads )
        self.SetBool( self.SubmitSceneBoxID, initSubmitScene )
        self.SetBool( self.ExportProjectBoxID, initExportProject )
        self.SetLong( self.BuildBoxID, selectedBuildID )
        self.SetBool( self.LocalRenderingBoxID, initLocalRendering )
        
        self.SetLong( self.IntegrationTypeBoxID, self.integrationType )
        
        self.SetBool( self.SubmitDraftJobBoxID, initSubmitDraftJob )
        self.SetBool( self.UseQuickDraftBoxID, initUseQuickDraft )
        self.EnableDraftFields()
        
        self.SetString( self.DraftTemplateBoxID, initDraftTemplate )
        self.SetString( self.DraftUserBoxID, initDraftUser )
        self.SetString( self.DraftEntityBoxID, initDraftEntity )
        self.SetString( self.DraftVersionBoxID, initDraftVersion )
        self.SetString( self.DraftExtraArgsBoxID, initDraftExtraArgs )
        
        self.SetLong( self.QuickDraftFormatID, selectedFormat )
        self.SetLong( self.QuickDraftResolutionID, selectedResolution )
        self.AdjustCodecs()
        self.SetLong( self.QuickDraftCodecID, selectedCodec )
        self.AdjustQuality()
        self.SetLong( self.QuickDraftQualityID, initQuickDraftQuality )
        self.AdjustFrameRates()
        self.SetLong( self.QuickDraftFrameRateID, selectedFrameRate )
        
        self.Enable( self.SubmitSceneBoxID, not initExportProject )
        
        self.PulledFTrackJobSettings = self.getFtrackData()
        if self.PulledFTrackJobSettings != None and len(self.PulledFTrackJobSettings) == 8:
            
            self.FTrackJobSettings = self.PulledFTrackJobSettings
            self.PulledFTrackJobSettings = {}
        else:
            self.FTrackJobSettings = {}
        
        #If 'CustomSanityChecks.py' exists, then it executes. This gives the user the ability to change default values
        if os.name == 'nt':
            self.SanityCheckFile = self.DeadlineRepositoryRoot + "\\submission\\Cinema4D\\Main\\CustomSanityChecks.py"
        else:
            self.SanityCheckFile = self.DeadlineRepositoryRoot + "/submission/Cinema4D/Main/CustomSanityChecks.py"
            
        if os.path.isfile( self.SanityCheckFile ):
            print ( "Running sanity check script: " + self.SanityCheckFile )
            try:
                import CustomSanityChecks
                sanityResult = CustomSanityChecks.RunSanityCheck( self )
                if not sanityResult:
                    print( "Sanity check returned False, exiting" )
                    self.Close()
            except:
                gui.MessageDialog( "Could not run CustomSanityChecks.py script: " + traceback.format_exc() )
        
        return True

    def getTakeFrames( self, s ):
        try:
            start = s.index( "<%" ) + len( "<%" )
            end = s.index( "%>", start )
            return s[start:end]
        except ValueError:
            return ""

    def stripTakeName( self, s ):
        try:
            start = s.index( "<%"  )
            end = s.index( "%>" )
            return s.replace(s[start:end+2], "")
        except ValueError:
            return ""

    
    def getFtrackData( self ):
        # get ftrack data from launched app
        import os
        try:
            import ftrack
        except:
            return {}
            
        import json
        import base64
        decodedEventData = json.loads(
            base64.b64decode(
                os.environ.get('FTRACK_CONNECT_EVENT')
            )
        )
        taskId = decodedEventData.get('selection')[0]['entityId']
        user = decodedEventData.get('source')['user']
        task = ftrack.Task(taskId)
        
        ftrackData = {}
        ftrackData["FT_Username"] = user['username']
        ftrackData["FT_TaskName"] = task.getName()
        ftrackData["FT_TaskId"] = task.getId()
        ftrackData["FT_Description"] = task.getDescription()
        try:
            project = task.getProject()
            ftrackData["FT_ProjectName"] = project.getName()
            ftrackData["FT_ProjectId"] = project.getId()
        except:
            pass
        
        try:
            asset = task.getAssets()[0]
            ftrackData[ "FT_AssetName" ] = asset.getName()
            ftrackData["FT_AssetId"] = asset.getId()
        except:
            pass
        
        return ftrackData

    def ValidQuality( self, selectedFormat, selectedCodec, enableQuality ):
        if selectedFormat in self.RestrictionsDict:
            if enableQuality in self.RestrictionsDict[selectedFormat]:
                validQualityCodecs = self.RestrictionsDict[selectedFormat][enableQuality]
                if selectedCodec in (codec.lower() for codec in validQualityCodecs):
                    return True
        return False

    def EnableDraftFields( self ):
        draftEnabled = self.GetBool( self.SubmitDraftJobBoxID )
        draftQuickEnabled = self.GetBool( self.UseQuickDraftBoxID )
        useIntegration = self.GetBool( self.UseIntegrationBoxID )

        selectedFormat = self.Formats[self.GetLong( self.QuickDraftFormatID )]
        isMovie = (self.FormatsDict[selectedFormat][1] == "movie")

        self.Enable( self.UseQuickDraftBoxID, draftEnabled )

        self.Enable( self.DraftTemplateBoxID, draftEnabled and not draftQuickEnabled )
        self.Enable( self.DraftTemplateButtonID, draftEnabled and not draftQuickEnabled )
        self.Enable( self.DraftUserBoxID, draftEnabled and not draftQuickEnabled )
        self.Enable( self.DraftEntityBoxID, draftEnabled and not draftQuickEnabled )
        self.Enable( self.DraftVersionBoxID, draftEnabled and not draftQuickEnabled )
        self.Enable( self.DraftExtraArgsBoxID, draftEnabled and not draftQuickEnabled )

        self.Enable( self.UploadDraftToShotgunBoxID, draftEnabled and not draftQuickEnabled and useIntegration )
        self.Enable( self.DraftUseShotgunDataButtonID, draftEnabled and not draftQuickEnabled and useIntegration )

        self.Enable( self.QuickDraftFormatID, draftEnabled and draftQuickEnabled )
        self.Enable( self.QuickDraftResolutionID, draftEnabled and draftQuickEnabled )
        self.Enable( self.QuickDraftCodecID, draftEnabled and draftQuickEnabled )
        self.Enable( self.QuickDraftFrameRateID, draftEnabled and draftQuickEnabled and isMovie )

        self.AdjustQuality()

    def AdjustCodecs( self ):
        selectedFormat = self.Formats[self.GetLong( self.QuickDraftFormatID )]
        format = self.FormatsDict[selectedFormat][0]
        selectedCodecID = self.GetLong(self.QuickDraftCodecID)
        currentCodec = self.CurrentCodecs[ selectedCodecID ]
        self.CurrentCodecs = self.GetOptions(self.FormatsDict[selectedFormat][0], "Codec", self.CodecsDict[format])

        id = -1
        self.FreeChildren(self.QuickDraftCodecID)
        for i in range( 0, len(self.CurrentCodecs) ):
            self.AddChild( self.QuickDraftCodecID, i, self.CurrentCodecs[ i ] )
            if self.CurrentCodecs[i] == currentCodec:
                id = i

        if id < 0:
            id = 0

        self.SetLong(self.QuickDraftCodecID,id)

    def AdjustFrameRates( self ):
        selectedFormat = self.Formats[self.GetLong( self.QuickDraftFormatID )]
        format = self.FormatsDict[selectedFormat][0]
        selectedCodecID = self.GetLong(self.QuickDraftCodecID)
        currentCodec = self.CurrentCodecs[selectedCodecID]
        self.CurrentCodecs = self.GetOptions(self.FormatsDict[selectedFormat][0], "Codec", self.CodecsDict[format])
        isMovie = (self.FormatsDict[selectedFormat][1] == "movie")
        selectedFrameRateID = self.GetLong(self.QuickDraftFrameRateID)
        currentFrameRate = self.CurrentFrameRates[ selectedFrameRateID ]

        self.CurrentFrameRates = self.GetOptions( format, "FrameRate", self.FrameRates )
        self.CurrentFrameRates = self.GetOptions( currentCodec, "FrameRate", self.CurrentFrameRates )

        id = -1
        self.FreeChildren(self.QuickDraftFrameRateID)
        for i in range( 0, len(self.CurrentFrameRates) ):
            self.AddChild( self.QuickDraftFrameRateID, i, self.CurrentFrameRates[ i ] )
            if self.CurrentFrameRates[i] == currentFrameRate:
                id = i

        if id < 0:
            id = 0

        self.SetLong(self.QuickDraftFrameRateID,id)

        self.Enable( self.QuickDraftFrameRateID, isMovie )

    def AdjustQuality( self ):
        draftEnabled = self.GetBool( self.SubmitDraftJobBoxID )
        draftQuickEnabled = self.GetBool( self.UseQuickDraftBoxID )
        selectedFormat = self.Formats[self.GetLong( self.QuickDraftFormatID )]
        format = self.FormatsDict[selectedFormat][0]
        self.CurrentCodecs = self.GetOptions(self.FormatsDict[selectedFormat][0], "Codec", self.CodecsDict[format])
        selectedCodec = self.CurrentCodecs[ self.GetLong(self.QuickDraftCodecID) ]
        draftQualityEnabled = self.ValidQuality( format, selectedCodec, "EnableQuality" )

        self.Enable( self.QuickDraftQualityID, draftEnabled and draftQuickEnabled and draftQualityEnabled )

    ## This is called when a user clicks on a button or changes the value of a field.
    def Command( self, id, msg ):
        # The Limit Group browse button was pressed.
        if id == self.LimitGroupsButtonID:
            c4d.StatusSetSpin()
            
            currLimitGroups = self.GetString( self.LimitGroupsBoxID )
            result = CallDeadlineCommand( ["-selectlimitgroups",currLimitGroups] )
            result = result.replace( "\n", "" ).replace( "\r", "" )
            
            if result != "Action was cancelled by user":
                self.SetString( self.LimitGroupsBoxID, result )
            
            c4d.StatusClear()
        
        # The Dependencies browse button was pressed.
        elif id == self.DependenciesButtonID:
            c4d.StatusSetSpin()
            
            currDependencies = self.GetString( self.DependenciesBoxID )
            result = CallDeadlineCommand( ["-selectdependencies",currDependencies] )
            result = result.replace( "\n", "" ).replace( "\r", "" )
            
            if result != "Action was cancelled by user":
                self.SetString( self.DependenciesBoxID, result )
            
            c4d.StatusClear()
        
        elif id == self.MachineListButtonID:
            c4d.StatusSetSpin()
            
            currMachineList = self.GetString( self.MachineListBoxID )
            result = CallDeadlineCommand( ["-selectmachinelist",currMachineList] )
            result = result.replace( "\n", "" ).replace( "\r", "" )
            
            if result != "Action was cancelled by user":
                self.SetString( self.MachineListBoxID, result )
            
            c4d.StatusClear()
        
        elif id == self.ExportProjectBoxID:
            self.Enable( self.SubmitSceneBoxID, not self.GetBool( self.ExportProjectBoxID ) )
        
        elif id == self.ConnectToIntegrationButtonID:
            c4d.StatusSetSpin()
            
            try:
                script = ""
                additionalArgs = []
                if self.integrationType == 0:
                    script = ("%s/events/Shotgun/ShotgunUI.py" % self.DeadlineRepositoryRoot)
                    
                    user = self.ShotgunJobSettings.get( 'UserName', "" )
                    if user != "":
                        additionalArgs.append("UserName="+user)
                    
                    task = self.ShotgunJobSettings.get( 'TaskName', "" )
                    if task != "":
                        additionalArgs.append("TaskName="+task)
                        
                    project = self.ShotgunJobSettings.get( 'ProjectName', "" )
                    if project != "":
                        additionalArgs.append("ProjectName="+project)
                    
                    entity = self.ShotgunJobSettings.get( 'EntityName', "" )
                    if entity != "":
                        additionalArgs.append("EntityName="+entity)
                    
                    version = self.ShotgunJobSettings.get( 'SequenceName', "" )
                    if version != "":
                        additionalArgs.append("SequenceName="+version)                  
                elif self.integrationType == 1:
                    script = ("%s/submission/FTrack/Main/FTrackUI.py" % self.DeadlineRepositoryRoot)
                    settings = self.PulledFTrackJobSettings
                    if len(settings) == 0:
                        settings = self.FTrackJobSettings
                    
                    user = settings.get( 'FT_Username', "" )
                    if user != "":
                        additionalArgs.append("UserName="+user)
                    
                    task = settings.get( 'FT_TaskName', "" )
                    if task != "":
                        additionalArgs.append("TaskName="+task)
                        
                    project = settings.get( 'FT_ProjectName', "" )
                    if project != "":
                        additionalArgs.append("ProjectName="+project)
                    
                    asset = settings.get( 'FT_AssetName', "" )
                    if asset != "":
                        additionalArgs.append("AssetName="+asset)
                elif self.integrationType == 2:
                    script = ("%s/events/NIM/NIM_UI.py" % self.DeadlineRepositoryRoot)
                    
                    for key,value in self.NimJobSettings.iteritems():
                        additionalArgs.append(key+"="+value)

                args = [ "-ExecuteScript", script, "Cinema4D" ]
                args.extend(additionalArgs)
                output = CallDeadlineCommand( args, False )
                outputLines = output.splitlines()
                
                tempKVPs = {}
                
                for line in outputLines:
                    line = line.strip()
                    tokens = line.split( '=', 1 )
                    if not line.startswith("("):
                        if len( tokens ) > 1:
                            key = tokens[0]
                            value = tokens[1]
                            tempKVPs[key] = value
                                
                if len( tempKVPs ) > 0:
                    if self.integrationType == 0:
                        self.ShotgunJobSettings = tempKVPs
                    elif self.integrationType == 1:
                        self.FTrackJobSettings = tempKVPs
                        self.PulledFTrackJobSettings = {}
                    elif self.integrationType == 2:
                        self.NimJobSettings = tempKVPs
                self.updateDisplay()
                
                self.Command( self.UseIntegrationBoxID, None )				
            finally:
                c4d.StatusClear()
        
        elif id == self.UseIntegrationBoxID:
            enable = self.GetBool( self.UseIntegrationBoxID )
            self.Enable( self.IntegrationVersionBoxID, enable )
            self.Enable( self.IntegrationDescriptionBoxID, enable )
            self.Enable( self.UploadMovieBoxID, enable )
            self.Enable( self.UploadFilmStripBoxID, enable and self.integrationType == 0 )
            
            enable = (enable and self.GetBool( self.SubmitDraftJobBoxID ))
            self.Enable( self.UploadDraftToShotgunBoxID, enable )
            self.Enable( self.DraftUseShotgunDataButtonID, enable )
            
            #~ if self.integrationType == 2:
                #~ self.Enable( self.IntegrationVersionBoxID, enable )
                #~ self.Enable( self.IntegrationDescriptionBoxID, enable )
                #~ self.Enable( self.UploadMovieBoxID, False )
                #~ self.Enable( self.UploadFilmStripBoxID, False )
                
                #~ enable = (enable and self.GetBool( self.SubmitDraftJobBoxID ))
                #~ self.Enable( self.UploadDraftToShotgunBoxID, enable )
                #~ self.Enable( self.DraftUseShotgunDataButtonID, enable )
                
        elif id == self.IntegrationVersionBoxID:
            if integrationType == 0: 
                self.ShotgunJobSettings[ 'VersionName' ] = self.GetString( self.IntegrationVersionBoxID )
            elif self.integrationType == 1:
                self.FTrackJobSettings[ 'FT_AssetName' ] = self.GetString( self.IntegrationVersionBoxID )
            elif self.integrationType == 2:
                self.NimJobSettings[ 'nim_renderName' ] = self.GetString( self.IntegrationVersionBoxID )
                
        elif id == self.IntegrationDescriptionBoxID:
            if self.integrationType == 0: 
                self.ShotgunJobSettings[ 'Description' ] = self.GetString( self.IntegrationDescriptionBoxID )
            elif integrationType == 1:
                self.FTrackJobSettings[ 'FT_Description' ] = self.GetString( self.IntegrationVersionBoxID )
            elif integrationType == 2:
                self.NimJobSettings[ 'nim_description' ] = self.GetString( self.IntegrationDescriptionBoxID )
                
        elif id == self.IntegrationTypeBoxID:
            self.integrationType = self.GetLong(self.IntegrationTypeBoxID)
            
            if self.integrationType == 2:
                self.SetString(self.UseIntegrationBoxID, "Add NIM render" )
                self.SetString(self.UploadDraftToShotgunBoxID,"Upload Draft Results To NIM")
                self.SetString(self.DraftUseShotgunDataButtonID, "Use NIM Data" )
            elif self.integrationType == 1:
                self.SetString(self.UseIntegrationBoxID, "Create new version" )
                self.SetString(self.UploadDraftToShotgunBoxID,"Upload Draft Results To FTrack")
                self.SetString(self.DraftUseShotgunDataButtonID, "Use FTrack Data" )
            else:
                self.SetString(self.UseIntegrationBoxID, "Create new version" )
                self.SetString(self.UploadDraftToShotgunBoxID,"Upload Draft Results To Shotgun")
                self.SetString(self.DraftUseShotgunDataButtonID, "Use Shotgun Data" )
                
            #self.LayoutChanged(self.uploadLayout)
            #self.updateDisplay()
            
            enable = self.GetBool( self.UseIntegrationBoxID )
            self.Enable( self.IntegrationVersionBoxID, enable )
            self.Enable( self.IntegrationDescriptionBoxID, enable )
            self.Enable( self.UploadMovieBoxID, enable )
            self.Enable( self.UploadFilmStripBoxID, enable and self.integrationType == 0 )
            
            enable = (enable and self.GetBool( self.SubmitDraftJobBoxID ))
            self.Enable( self.UploadDraftToShotgunBoxID, enable )
            self.Enable( self.DraftUseShotgunDataButtonID, enable )
            
            self.LayoutChanged(self.uploadLayout)
            self.updateDisplay()
            
        elif id == self.SubmitDraftJobBoxID:
            self.EnableDraftFields()

        elif id == self.UseQuickDraftBoxID:
            self.EnableDraftFields()
        
        elif id == self.QuickDraftFormatID:
            self.AdjustCodecs()
            self.AdjustFrameRates()
            self.EnableDraftFields()
                    
        elif id == self.QuickDraftCodecID:
            self.AdjustFrameRates()
            self.AdjustQuality()

        elif id == self.DraftTemplateButtonID:
            c4d.StatusSetSpin()
            
            try:
                currTemplate = self.GetString( self.DraftTemplateBoxID )
                result = CallDeadlineCommand( ["-SelectFilenameLoad", currTemplate] )
                
                if result != "Action was cancelled by user" and result != "":
                    self.SetString( self.DraftTemplateBoxID, result )
            finally:
                c4d.StatusClear()
            
        elif id == self.DraftUseShotgunDataButtonID:
            
            if self.integrationType == 0:
                shotgunValues = self.GetString( self.IntegrationInfoBoxID ).split( '\n' )
                
                user = self.ShotgunJobSettings.get( 'UserName', "" )
                task = self.ShotgunJobSettings.get( 'TaskName', "" )
                project = self.ShotgunJobSettings.get( 'ProjectName', "" )
                entity = self.ShotgunJobSettings.get( 'EntityName', "" )
                version = self.ShotgunJobSettings.get( 'VersionName', "" )
                draftTemplate = self.ShotgunJobSettings.get( 'DraftTemplate', "" )
                
                if task.strip() != "" and task.strip() != "None":
                    self.SetString( self.DraftEntityBoxID, task )
                elif project.strip() != "" and entity.strip() != "":
                    self.SetString( self.DraftEntityBoxID, "%s > %s" % (project, entity) )
                    
                if draftTemplate.strip() != "" and draftTemplate != "None":
                    self.SetString( self.DraftTemplateBoxID, draftTemplate )
            
            elif self.integrationType == 1:
                user = self.FTrackJobSettings.get( 'FT_Username', "" )
                version = self.FTrackJobSettings.get( 'FT_AssetName', "" )
                
                entity = self.FTrackJobSettings.get( 'FT_TaskName', "" )
                self.SetString( self.DraftEntityBoxID, entity )
                
            elif self.integrationType == 2:
                user = self.NimJobSettings.get( 'nim_user', "" )
                version = self.NimJobSettings.get( 'nim_renderName', "" )
                
                task = self.NimJobSettings.get( 'nim_taskID', "" )
                asset = self.NimJobSettings.get( 'nim_assetName', "" )
                shotName = self.NimJobSettings.get( 'nim_shotName', "" )
                
                entity = ""
                if len(asset) > 0:
                    entity = asset
                elif len(shotName) > 0:
                    entity = shotName
                
                if len(task) > 0:
                    self.SetString( self.DraftEntityBoxID, task )
                else:
                    self.SetString( self.DraftEntityBoxID, entity )
                    
            #set any relevant values
            self.SetString( self.DraftUserBoxID, user )
            self.SetString( self.DraftVersionBoxID, version )
        
        # The Submit or the Cancel button was pressed.
        elif id == self.SubmitButtonID or id == self.CancelButtonID:
            jobName = self.GetString( self.NameBoxID )
            comment = self.GetString( self.CommentBoxID )
            department = self.GetString( self.DepartmentBoxID )
            
            pool = self.Pools[ self.GetLong( self.PoolBoxID ) ]
            secondaryPool = self.SecondaryPools[ self.GetLong( self.SecondaryPoolBoxID ) ]
            group = self.Groups[ self.GetLong( self.GroupBoxID ) ]
            priority = self.GetLong( self.PriorityBoxID )
            machineLimit = self.GetLong( self.MachineLimitBoxID )
            taskTimeout = self.GetLong( self.TaskTimeoutBoxID )
            autoTaskTimeout = self.GetBool( self.AutoTimeoutBoxID )
            concurrentTasks = self.GetLong( self.ConcurrentTasksBoxID )
            limitConcurrentTasks = self.GetBool( self.LimitConcurrentTasksBoxID )
            isBlacklist = self.GetBool( self.IsBlacklistBoxID )
            machineList = self.GetString( self.MachineListBoxID )
            limitGroups = self.GetString( self.LimitGroupsBoxID )
            dependencies = self.GetString( self.DependenciesBoxID )
            onComplete = self.OnComplete[ self.GetLong( self.OnCompleteBoxID ) ]
            submitSuspended = self.GetBool( self.SubmitSuspendedBoxID )

            # activeTake = self.GetString( self.TakesBoxID )
            activeTake = self.Takes[ self.GetLong( self.TakesBoxID ) ]

            frames = self.GetString( self.FramesBoxID )
            chunkSize = self.GetLong( self.ChunkSizeBoxID )
            threads = self.GetLong( self.ThreadsBoxID )
            build = self.Builds[ self.GetLong( self.BuildBoxID ) ]
            submitScene = self.GetBool( self.SubmitSceneBoxID )
            exportProject = self.GetBool( self.ExportProjectBoxID )
            localRendering = self.GetBool( self.LocalRenderingBoxID )
            
            submitDraftJob = self.GetBool( self.SubmitDraftJobBoxID )
            useQuickDraft = self.GetBool( self.UseQuickDraftBoxID )
            
            draftTemplate = self.GetString( self.DraftTemplateBoxID )
            draftUser = self.GetString( self.DraftUserBoxID )
            draftEntity = self.GetString( self.DraftEntityBoxID )
            draftVersion = self.GetString( self.DraftVersionBoxID )
            draftExtraArgs = self.GetString( self.DraftExtraArgsBoxID )
            
            QuickDraftFormat = self.Formats[self.GetLong(self.QuickDraftFormatID)]
            QuickDraftResolution = self.Resolutions[self.GetLong(self.QuickDraftResolutionID)]
            QuickDraftCodec = self.CurrentCodecs[self.GetLong(self.QuickDraftCodecID)]
            QuickDraftQuality = self.GetLong( self.QuickDraftQualityID )
            QuickDraftFrameRate = self.CurrentFrameRates[self.GetLong(self.QuickDraftFrameRateID)]
    
            IncludeMainTake = self.GetBool( self.IncludeMainBoxID )
    
            # Save sticky settings
            try:
                config = ConfigParser.ConfigParser()
                config.add_section( "Sticky" )
                
                config.set( "Sticky", "Department", department )
                config.set( "Sticky", "Pool", pool )
                config.set( "Sticky", "SecondaryPool", secondaryPool )
                config.set( "Sticky", "Group", group )
                config.set( "Sticky", "Priority", str(priority) )
                config.set( "Sticky", "MachineLimit", str(machineLimit) )
                config.set( "Sticky", "IsBlacklist", str(isBlacklist) )
                config.set( "Sticky", "MachineList", machineList )
                config.set( "Sticky", "LimitGroups", limitGroups )
                config.set( "Sticky", "SubmitSuspended", str(submitSuspended) )
                config.set( "Sticky", "ChunkSize", str(chunkSize) )
                config.set( "Sticky", "Threads", str(threads) )
                config.set( "Sticky", "Build", build )
                config.set( "Sticky", "SubmitScene", str(submitScene) )
                config.set( "Sticky", "ExportProject", str(exportProject) )
                config.set( "Sticky", "LocalRendering", str(localRendering) )
                
                config.set( "Sticky", "SubmitDraftJob", submitDraftJob )
                config.set( "Sticky", "UseQuickDraft", useQuickDraft )
                
                config.set( "Sticky", "DraftTemplate", draftTemplate )
                config.set( "Sticky", "DraftUser", draftUser )
                config.set( "Sticky", "DraftEntity", draftEntity )
                config.set( "Sticky", "DraftVersion", draftVersion )
                config.set( "Sticky", "DraftExtraArgs", draftExtraArgs )
                
                config.set( "Sticky", "QuickDraftFormat", QuickDraftFormat )
                config.set( "Sticky", "QuickDraftResolution", QuickDraftResolution )
                config.set( "Sticky", "QuickDraftCodec", QuickDraftCodec )
                config.set( "Sticky", "QuickDraftQuality", QuickDraftQuality )
                config.set( "Sticky", "QuickDraftFrameRate", QuickDraftFrameRate )
                
                config.set( "Sticky", "IncludeMainTake", IncludeMainTake )
                
                fileHandle = open( self.ConfigFile, "w" )
                config.write( fileHandle )
                fileHandle.close()
            except:
                print( "Could not write sticky settings" )
            
            # Close the dialog if the Cancel button was clicked
            if id == self.SubmitButtonID:
                groupBatch = False
                takesToRender = []
                # If takes is set to All, remove All and Main from list
                if self.Takes[ self.GetLong( self.TakesBoxID ) ] == "All":
                    self.Takes.remove("All")
                    self.Takes.remove(" ")
                    
                    #This will only fail in C4D R17 without a service pack
                    try:
                        self.Takes.remove("Marked")
                    except:
                        pass
                        
                    if not self.GetBool(self.IncludeMainBoxID):
                        self.Takes.remove("Main")
                    takesToRender = self.Takes # Set takesToRender to the remaining takes
                    groupBatch = True
                elif self.Takes[ self.GetLong( self.TakesBoxID ) ] == "Marked":
                    # Set Takes setting
                    takesToRender = []
                    doc = documents.GetActiveDocument()
                    takeData = doc.GetTakeData()
                    take = takeData.GetMainTake()
                    while take:
                        if take.IsChecked():
                            name = take.GetName() # this is the take name
                            takesToRender.append( name )
                        take = GetNextObject(take)
                    groupBatch = True
                     
                else:
                    if activeTake == " ":
                        activeTake = ""
                    takesToRender.append( activeTake )
                
                successes = 0
                failures = 0
                submissionSuccess = 0
                # Loop through the list of takes and submit them all
                for take in takesToRender:
                    if exportProject:
                        scene = documents.GetActiveDocument()
                        sceneName = scene.GetDocumentName()
                        originalSceneFilename = os.path.join( scene.GetDocumentPath(), sceneName )
                        
                        print( "Exporting scene" )
                        c4d.StatusSetSpin()
                        c4d.CallCommand( 12255 )
                        c4d.StatusClear()
                        
                        scene = documents.GetActiveDocument()
                        sceneName = scene.GetDocumentName()
                        newSceneFilename = os.path.join( scene.GetDocumentPath(), sceneName )
                        
                        # If the scene file name hasn't changed, that means that they canceled the export dialog.
                        if newSceneFilename == originalSceneFilename:
                            return True
                        
                        #continueOn = gui.QuestionDialog( "After the export, the scene file path is now:\n\n" + sceneFilename + "\n\nDo you wish to continue with the submission?" )
                        #if not continueOn:
                        #	return True
                        
                        submitScene = False # can't submit scene if it's being exported
                    
                    scene = documents.GetActiveDocument()
                    sceneName = scene.GetDocumentName()
                    #sceneFilename = scene.GetDocumentPath() + "/" + sceneName
                    scenePath = scene.GetDocumentPath()
                    sceneFilename = os.path.join( scenePath, sceneName )
                    renderData = scene.GetActiveRenderData().GetData()
                    
                    saveOutput = renderData.GetBool( c4d.RDATA_SAVEIMAGE )
                    outputPath = renderData.GetFilename( c4d.RDATA_PATH )
                    if not os.path.isabs( outputPath ):
                        outputPath = os.path.join( scenePath, outputPath )
                    outputFormat = renderData.GetLong( c4d.RDATA_FORMAT )
                    outputName = renderData.GetLong( c4d.RDATA_NAMEFORMAT )
                    
                    saveMP = renderData.GetBool( c4d.RDATA_MULTIPASS_ENABLE ) and renderData.GetBool( c4d.RDATA_MULTIPASS_SAVEIMAGE )
                    mpPath = renderData.GetFilename( c4d.RDATA_MULTIPASS_FILENAME )
                    if not os.path.isabs( mpPath ):
                        mpPath = os.path.join( scenePath, mpPath )
                    mpFormat = renderData.GetLong( c4d.RDATA_MULTIPASS_SAVEFORMAT )
                    mpOneFile = renderData.GetBool( c4d.RDATA_MULTIPASS_SAVEONEFILE )
                    
                    width = renderData.GetLong( c4d.RDATA_XRES )
                    height = renderData.GetLong( c4d.RDATA_YRES )
                    
                    print( "Creating submit info file" )
                    
                    # Create the submission info file
                    jobInfoFile = self.DeadlineTemp + "/c4d_submit_info.job"
                    fileHandle = open( jobInfoFile, "w" )
                    fileHandle.write( "Plugin=Cinema4D\n" )
                    
                    tempJobName = jobName
                    if not take == "Main" and not take == "" :
                        tempJobName = tempJobName + " - " + take
                    
                    fileHandle.write( "Name=%s\n" % tempJobName )
                    fileHandle.write( "Comment=%s\n" % comment )
                    fileHandle.write( "Department=%s\n" % department )
                    fileHandle.write( "Group=%s\n" % group )
                    fileHandle.write( "Pool=%s\n" % pool )
                    if secondaryPool == " ": # If it's a space, then no secondary pool was selected.
                        fileHandle.write( "SecondaryPool=\n" )
                    else:
                        fileHandle.write( "SecondaryPool=%s\n" % secondaryPool )
                    fileHandle.write( "Priority=%s\n" % priority )
                    fileHandle.write( "MachineLimit=%s\n" % machineLimit )
                    fileHandle.write( "TaskTimeoutMinutes=%s\n" % taskTimeout )
                    fileHandle.write( "EnableAutoTimeout=%s\n" % autoTaskTimeout )
                    fileHandle.write( "ConcurrentTasks=%s\n" % concurrentTasks )
                    fileHandle.write( "LimitConcurrentTasksToNumberOfCpus=%s\n" % limitConcurrentTasks )
                    fileHandle.write( "LimitGroups=%s\n" % limitGroups )
                    fileHandle.write( "OnJobComplete=%s\n" % onComplete )
                    fileHandle.write( "Frames=%s\n" % frames )
                    fileHandle.write( "ChunkSize=%s\n" % chunkSize )
                    if submitSuspended:
                        fileHandle.write( "InitialStatus=Suspended\n" )
                    
                    if isBlacklist:
                        fileHandle.write( "Blacklist=%s\n" % machineList )
                    else:
                        fileHandle.write( "Whitelist=%s\n" % machineList )
                    
                    outputFilenameLine = False
                    outputDirectoryLine = False
                    if saveOutput and outputPath != "":
                        outputFilename = self.GetOutputFileName( outputPath, outputFormat, outputName )
                        if outputFilename != "":
                            doc = documents.GetActiveDocument()
                            context = self.get_token_context(doc, take=take, passName = "rgb", userPass ="RGB")
                            tempOutputFileName = self.token_eval(outputFilename, context)
                            fileHandle.write( "OutputFilename0=%s\n" % tempOutputFileName )
                            outputFilenameLine = True
                        else:
                            fileHandle.write( "OutputDirectory0=%s\n" % os.path.dirname( outputPath ) )
                            outputDirectoryLine = True
                    
                    if saveMP and mpPath != "":
                        #1016606 = EXR
                        if mpOneFile and ( mpFormat == c4d.FILTER_B3D or mpFormat == c4d.FILTER_PSD or mpFormat == c4d.FILTER_PSB or mpFormat == c4d.FILTER_TIF_B3D or mpFormat == c4d.FILTER_TIF or mpFormat == 1016606 ):
                            mpFilename = self.GetOutputFileName( mpPath, mpFormat, outputName )
                            if mpFilename != "":
                                doc = documents.GetActiveDocument()
                                context = self.get_token_context(doc, take=take)
                                tempMpFilename = self.token_eval(mpFilename, context)
                                if not outputFilenameLine and not outputDirectoryLine:
                                    fileHandle.write( "OutputFilename0=%s\n" % tempMpFilename )
                                elif outputFilenameLine:
                                    fileHandle.write( "OutputFilename1=%s\n" % tempMpFilename )
                            else:
                                if not outputFilenameLine and not outputDirectoryLine:
                                    fileHandle.write( "OutputDirectory0=%s\n" % os.path.dirname( mpPath ) )
                                elif outputDirectoryLine:
                                    fileHandle.write( "OutputDirectory1=%s\n" % os.path.dirname( mpPath ) )
                        else:
                            mPass = scene.GetActiveRenderData().GetFirstMultipass()
                            #"Post Effects":"",  not supported: NO files were made throughout my  testing so no idea what this should be
                            mPassTypePrefix ={
                                                "Ambient":"ambient",
                                                "Diffuse":"diffuse",
                                                "Specular":"specular",
                                                "Shadow":"shadow",
                                                "Reflection":"refl",
                                                "Refraction":"refr",
                                                "Ambient Occlusion":"ao",
                                                "Global Illumination":"gi",
                                                "Caustics":"caustics",
                                                "Atmosphere":"atmos",
                                                "Atmosphere (Multiply)":"atmosmul",
                                                "Material Color":"matcolor",
                                                "Material Diffusion":"matdif",
                                                "Material Luminance":"matlum",
                                                "Material Transparency":"mattrans",
                                                "Material Reflection":"matrefl",
                                                "Material Environment":"matenv",
                                                "Material Specular":"matspec",
                                                "Material Specular Color":"matspeccol",
                                                "Material Normal":"normal",
                                                "Material UVW":"uv",
                                                "RGBA Image":"rgb",
                                                "Motion Vector":"motion",
                                                "Illumination":"illum",
                                                "Depth":"depth"
                                            }
                            count = 1
                            if not outputFilenameLine and not outputDirectoryLine:
                                count = 0
                            while mPass is not None:
                                if not mPass.GetBit(c4d.BIT_VPDISABLED):
                                    try:
                                        doc = documents.GetActiveDocument()
                                        context = self.get_token_context( doc, take=take, passName = mPassTypePrefix[mPass.GetTypeName()], userPass = mPass.GetName()  )
                                        mpFilename = self.GetOutputFileName( mpPath, mpFormat, outputName, "_"+str(mPassTypePrefix[mPass.GetTypeName()]) )
                                        tempMpFilename = self.token_eval(mpFilename, context)
                                        fileHandle.write( "OutputFilename%i=%s\n" % (count, tempMpFilename) )
                                        count += 1
                                    except:
                                        pass
                                mPass=mPass.GetNext()
                                                
                    
                    #Shotgun/Draft
                    extraKVPIndex = 0
                    
                    if self.GetBool( self.UseIntegrationBoxID ):
                        if self.integrationType == 0:
                            fileHandle.write( "ExtraInfo0=%s\n" % self.ShotgunJobSettings.get('TaskName', "") )
                            fileHandle.write( "ExtraInfo1=%s\n" % self.ShotgunJobSettings.get('ProjectName', "") )
                            fileHandle.write( "ExtraInfo2=%s\n" % self.ShotgunJobSettings.get('EntityName', "") )
                            fileHandle.write( "ExtraInfo3=%s\n" % self.ShotgunJobSettings.get('VersionName', "") )
                            fileHandle.write( "ExtraInfo4=%s\n" % self.ShotgunJobSettings.get('Description', "") )
                            fileHandle.write( "ExtraInfo5=%s\n" % self.ShotgunJobSettings.get('UserName', "") )
                            
                            for key in self.ShotgunJobSettings:
                                if key != 'DraftTemplate':
                                    fileHandle.write( "ExtraInfoKeyValue%d=%s=%s\n" % (extraKVPIndex, key, self.ShotgunJobSettings[key]) )
                                    extraKVPIndex += 1
                            if self.GetBool(self.UploadMovieBoxID):
                                fileHandle.write( "ExtraInfoKeyValue%s=Draft_CreateSGMovie=True\n" % (extraKVPIndex) )
                                extraKVPIndex += 1
                                groupBatch = True
                            if self.GetBool(self.UploadFilmStripBoxID):
                                fileHandle.write( "ExtraInfoKeyValue%s=Draft_CreateSGFilmstrip=True\n" % (extraKVPIndex) )
                                extraKVPIndex += 1
                                groupBatch = True
                                
                        elif self.integrationType == 1:
                            fileHandle.write( "ExtraInfo0=%s\n" % self.FTrackJobSettings.get('FT_TaskName', "") )
                            fileHandle.write( "ExtraInfo1=%s\n" % self.FTrackJobSettings.get('FT_ProjectName', "") )
                            fileHandle.write( "ExtraInfo2=%s\n" % self.FTrackJobSettings.get('FT_AssetName', "") )
                            #fileHandle.write( "ExtraInfo3=%s\n" % self.FTrackJobSettings.get('VersionName', "") )
                            fileHandle.write( "ExtraInfo4=%s\n" % self.FTrackJobSettings.get('FT_Description', "") )
                            fileHandle.write( "ExtraInfo5=%s\n" % self.FTrackJobSettings.get('FT_Username', "") )
                            for key in self.FTrackJobSettings:
                                fileHandle.write( "ExtraInfoKeyValue%d=%s=%s\n" % (extraKVPIndex, key, self.FTrackJobSettings[key]) )
                                extraKVPIndex += 1
                                
                            if self.GetBool(self.UploadMovieBoxID):
                                fileHandle.write( "ExtraInfoKeyValue%s=Draft_CreateFTMovie=True\n" % (extraKVPIndex) )
                                extraKVPIndex += 1
                                groupBatch = True
                                
                        elif self.integrationType == 2:
                            fileHandle.write( "ExtraInfo0=%s\n" % self.NimJobSettings.get('nim_renderName', "") )
                            fileHandle.write( "ExtraInfo1=%s\n" % self.NimJobSettings.get('nim_jobName', "") )
                            fileHandle.write( "ExtraInfo2=%s\n" % self.NimJobSettings.get('nim_showName', "") )
                            fileHandle.write( "ExtraInfo3=%s\n" % self.NimJobSettings.get('nim_shotName', "") )
                            fileHandle.write( "ExtraInfo4=%s\n" % self.NimJobSettings.get('nim_description', "") )
                            fileHandle.write( "ExtraInfo5=%s\n" % self.NimJobSettings.get('nim_user', "") )
                            for key in self.NimJobSettings:
                                fileHandle.write( "ExtraInfoKeyValue%d=%s=%s\n" % (extraKVPIndex, key, self.NimJobSettings[key]) )
                                extraKVPIndex += 1
                                
                            if self.GetBool(self.UploadMovieBoxID):
                                fileHandle.write( "ExtraInfoKeyValue%s=Draft_CreateNimMovie=True\n" % (extraKVPIndex) )
                                extraKVPIndex += 1
                                groupBatch = True
                                
                    if self.GetBool( self.SubmitDraftJobBoxID ):
                        if not self.GetBool( self.UseQuickDraftBoxID ):
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftTemplate=%s\n" % (extraKVPIndex, draftTemplate) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftUsername=%s\n" % (extraKVPIndex, draftUser) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftEntity=%s\n" % (extraKVPIndex, draftEntity) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftVersion=%s\n" % (extraKVPIndex, draftVersion) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftExtraArgs=%s\n" % (extraKVPIndex, draftExtraArgs ) )
                            extraKVPIndex += 1
                        else:
                            fileHandle.write( "ExtraInfoKeyValue%d=SubmitQuickDraft=True\n" % (extraKVPIndex) )
                            extraKVPIndex += 1
                            format = self.Formats[self.GetLong( self.QuickDraftFormatID )]
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftExtension=%s\n" % (extraKVPIndex, self.FormatsDict[format][0]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftType=%s\n" % (extraKVPIndex, self.FormatsDict[format][1]) )
                            extraKVPIndex += 1
                            resolution = self.Resolutions[ self.GetLong( self.QuickDraftResolutionID ) ]
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftResolution=%s\n" % (extraKVPIndex, self.ResolutionsDict[resolution]) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftCodec=%s\n" % (extraKVPIndex, self.CurrentCodecs[ self.GetLong( self.QuickDraftCodecID ) ] ) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftQuality=%s\n" % (extraKVPIndex, self.GetLong( self.QuickDraftQualityID )) )
                            extraKVPIndex += 1
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftFrameRate=%s\n" % (extraKVPIndex, self.CurrentFrameRates[ self.GetLong( self.QuickDraftFrameRateID ) ]) )
                            extraKVPIndex += 1
                            
                        if self.integrationType == 0:
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftUploadToShotgun=%s\n" % (extraKVPIndex, str(self.GetBool( self.UploadDraftToShotgunBoxID ) and self.GetBool( self.UseIntegrationBoxID ) and self.integrationType == 0) ) )
                            extraKVPIndex += 1
                        elif self.integrationType == 1:
                            fileHandle.write( "ExtraInfoKeyValue%d=FT_DraftUploadMovie=%s\n" % (extraKVPIndex, str(self.GetBool( self.UploadDraftToShotgunBoxID ) and self.GetBool( self.UseIntegrationBoxID ) and self.integrationType == 1) ) )
                            extraKVPIndex += 1
                        elif self.integrationType == 2:
                            fileHandle.write( "ExtraInfoKeyValue%d=DraftUploadToNim=%s\n" % (extraKVPIndex, str(self.GetBool( self.UploadDraftToShotgunBoxID ) and self.GetBool( self.UseIntegrationBoxID ) and self.integrationType == 2) ) )
                            extraKVPIndex += 1
                        groupBatch = True
                        
                    if groupBatch:
                        fileHandle.write( "BatchName=%s\n" % (jobName ) ) 
                    
                    fileHandle.close()
                    
                    print( "Creating plugin info file" )
                    
                    # Create the plugin info file
                    pluginInfoFile = self.DeadlineTemp + "/c4d_plugin_info.job"
                    fileHandle = open( pluginInfoFile, "w" )
                    if not submitScene:
                        fileHandle.write( "SceneFile=%s\n" % sceneFilename )
                    fileHandle.write( "Version=%s\n" % (c4d.GetC4DVersion() / 1000) )
                    fileHandle.write( "Build=%s\n" % build )
                    fileHandle.write( "Threads=%s\n" % threads )
                    fileHandle.write( "Width=%s\n" % width )
                    fileHandle.write( "Height=%s\n" % height )
                    fileHandle.write( "LocalRendering=%s\n" % localRendering )
                    fileHandle.write( "Take=%s\n" % take )
                    
                    if saveOutput and outputPath != "":
                        head, tail = os.path.split( outputPath )
                        fileHandle.write( "FilePath=%s\n" % head )
                        fileHandle.write( "FilePrefix=%s\n" % tail )
                        
                    if saveMP and mpPath != "":
                        head, tail = os.path.split( mpPath )
                        fileHandle.write( "MultiFilePath=%s\n" % head )
                        fileHandle.write( "MultiFilePrefix=%s\n" % tail )
                    
                    fileHandle.close()
                    
                    print( "Submitting job" )
                    c4d.StatusSetSpin()
                    
                    # Submit the job to Deadline
                    args = []
                    args.append( jobInfoFile )
                    args.append( pluginInfoFile )
                    if submitScene:
                        args.append( sceneFilename )
                    
                    results = ""
                    try:
                        results = CallDeadlineCommand( args )
                        submissionSuccess += 1
                    except:
                        results = "An error occurred while submitting the job to Deadline."
                    
                    print results
                    
                    if results.find( "Result=Success" ) != -1:
                        successes+=1
                    else:
                        failures+=1
                    
                c4d.StatusClear()
                if len(takesToRender) == 1:
                    gui.MessageDialog( results )
                elif len(takesToRender) > 1:
                    gui.MessageDialog( "Submission Results\n\nSuccesses: " + str(successes) + "\nFailures: " + str(failures) + "\n\nSee script console for more details" )
                else:
                    gui.MessageDialog( "Submission Failed.  No takes selected." )
            
            self.Close()
        
        return True
    
    def get_token_context(self, doc, take="", passName="", userPass = ""):
        if take == "" and useTakes:
            take = doc.GetTakeData().GetCurrentTake().GetName()
        rdata = doc.GetActiveRenderData()
        bd = doc.GetRenderBaseDraw()
        fps = doc.GetFps()
        time = doc.GetTime()
        range_ = (rdata[c4d.RDATA_FRAMEFROM], rdata[c4d.RDATA_FRAMETO])
        
        context = {
            'prj': doc.GetDocumentName(),
            'camera': bd.GetSceneCamera(doc).GetName(),
            'take': take,
            # 'pass': 
            # 'userpass':
            'frame': doc.GetTime().GetFrame(doc.GetFps()),
            'rs': rdata.GetName(),
            'res': '%dx%d' % (rdata[c4d.RDATA_XRES], rdata[c4d.RDATA_YRES]),
            'range': '%d-%d' % tuple(x.GetFrame(fps) for x in range_),
            'fps': fps}
        
        if not passName  == "":
            context['pass'] = passName
            
        if not userPass == "":
            context['userpass'] = userPass
        
        return context
        
    def token_eval(self, text, context):
        return TokenString(text).safe_substitute(context)
    
    def updateDisplay(self):
        displayText = ""
        if self.integrationType == 0:
            if 'UserName' in self.ShotgunJobSettings:
                displayText += "User Name: %s\n" % self.ShotgunJobSettings[ 'UserName' ]
            if 'TaskName' in self.ShotgunJobSettings:
                displayText += "Task Name: %s\n" % self.ShotgunJobSettings[ 'TaskName' ]
            if 'ProjectName' in self.ShotgunJobSettings:
                displayText += "Project Name: %s\n" % self.ShotgunJobSettings[ 'ProjectName' ]
            if 'EntityName' in self.ShotgunJobSettings:
                displayText += "Entity Name: %s\n" % self.ShotgunJobSettings[ 'EntityName' ]	
            if 'EntityType' in self.ShotgunJobSettings:
                displayText += "Entity Type: %s\n" % self.ShotgunJobSettings[ 'EntityType' ]
            if 'DraftTemplate' in self.ShotgunJobSettings:
                displayText += "Draft Template: %s\n" % self.ShotgunJobSettings[ 'DraftTemplate' ]
        
            self.SetString( self.IntegrationInfoBoxID, displayText )
            self.SetString( self.IntegrationVersionBoxID, self.ShotgunJobSettings.get( 'VersionName', "" ) )
            self.SetString( self.IntegrationDescriptionBoxID, self.ShotgunJobSettings.get( 'Description', "" ) )
            
        elif self.integrationType == 1:
            if 'FT_Username' in self.FTrackJobSettings:
                displayText += "User Name: %s\n" % self.FTrackJobSettings[ 'FT_Username' ]
            if 'FT_TaskName' in self.FTrackJobSettings:
                displayText += "Task Name: %s\n" % self.FTrackJobSettings[ 'FT_TaskName' ]
            if 'FT_ProjectName' in self.FTrackJobSettings:
                displayText += "Project Name: %s\n" % self.FTrackJobSettings[ 'FT_ProjectName' ]
        
            self.SetString( self.IntegrationInfoBoxID, displayText )
            self.SetString( self.IntegrationVersionBoxID, self.FTrackJobSettings.get( 'FT_AssetName', "" ) )
            self.SetString( self.IntegrationDescriptionBoxID, self.FTrackJobSettings.get( 'FT_Description', "" ) )
            
        elif self.integrationType == 2:
            if 'nim_taskID' in self.NimJobSettings:
                if self.NimJobSettings['nim_taskID']:
                    displayText += "Task ID: %s\n" % self.NimJobSettings[ 'nim_taskID' ]

                    if 'nim_useNim' in self.NimJobSettings:
                        displayText += "User Name: %s\n" % self.NimJobSettings[ 'nim_useNim' ]
                    if 'nim_basename' in self.NimJobSettings:
                        displayText += "User Name: %s\n" % self.NimJobSettings[ 'nim_basename' ]
                    if 'nim_user' in self.NimJobSettings:
                        displayText += "User Name: %s\n" % self.NimJobSettings[ 'nim_user' ]
                    if 'nim_jobName' in self.NimJobSettings:
                        displayText += "Job Name: %s\n" % self.NimJobSettings[ 'nim_jobName' ]
                    if 'nim_class' in self.NimJobSettings:
                        displayText += "Class: %s\n" % self.NimJobSettings[ 'nim_class' ]
                    if 'nim_assetName' in self.NimJobSettings:
                        displayText += "Asset Name: %s\n" % self.NimJobSettings[ 'nim_assetName' ]    
                    if 'nim_showName' in self.NimJobSettings:
                        displayText += "Show Name: %s\n" % self.NimJobSettings[ 'nim_showName' ]
                    if 'nim_shotName' in self.NimJobSettings:
                        displayText += "Shot Name: %s\n" % self.NimJobSettings[ 'nim_shotName' ]
                    if 'nim_jobID' in self.NimJobSettings:
                        displayText += "Job ID: %s\n" % self.NimJobSettings[ 'nim_jobID' ]
                    if 'nim_itemID' in self.NimJobSettings:
                        displayText += "Item ID: %s\n" % self.NimJobSettings[ 'nim_itemID' ]
                    if 'nim_fileID' in self.NimJobSettings:
                        displayText += "File ID: %s\n" % self.NimJobSettings[ 'nim_fileID' ]
                    if 'DraftTemplate' in self.NimJobSettings:
                        displayText += "Draft Template: %s\n" % self.NimJobSettings[ 'DraftTemplate' ]

                    if len(displayText)>0:
                        enableIntegration = True
                else:
                    displayText = "You must select a task to log a render in NIM"
                    enableIntegration = False

            self.SetString( self.IntegrationInfoBoxID, displayText )
            self.SetString( self.IntegrationVersionBoxID, self.NimJobSettings.get( 'nim_renderName', "" ) )
            self.SetString( self.IntegrationDescriptionBoxID, self.NimJobSettings.get( 'nim_description', "" ) )
            
        if len(displayText)>0:
            self.Enable( self.UseIntegrationBoxID, True )
            self.SetBool( self.UseIntegrationBoxID, True )
            self.Command( self.SubmitDraftJobBoxID, None )
        else:
            self.Enable( self.UseIntegrationBoxID, False )
            self.SetBool( self.UseIntegrationBoxID, False )   
        
    def GetOutputFileName( self, outputPath, outputFormat, outputName, appendPrefix = "" ):
        if outputPath == "":
            return ""
        
        # C4D always throws away the last extension in the file name, so we'll do that too.
        outputPrefix, tempOutputExtension = os.path.splitext( outputPath )
        outputExtension = self.GetExtensionFromFormat( outputFormat )
        outputPrefix = outputPrefix + appendPrefix
        # If the name requires an extension, and an extension could not be determined,
        # we simply return an empty output filename because we don't have all the info.
        if outputName == 0 or outputName == 3 or outputName == 6:
            if outputExtension == "":
                return ""
        
        # If the output ends with a digit, and the output name scheme doesn't start with a '.', then C4D automatically appends an underscore.
        if len( outputPrefix ) > 0 and outputPrefix[ len( outputPrefix ) - 1 ].isdigit() and outputName not in (2, 5, 6):
            outputPrefix = outputPrefix + "_"
        
        # Format the output filename based on the selected output name.
        if outputName == 0:
            return outputPrefix + "####." + outputExtension
        elif outputName == 1:
            return outputPrefix + "####"
        elif outputName == 2:
            return outputPrefix + ".####"
        elif outputName == 3:
            return outputPrefix + "###." + outputExtension
        elif outputName == 4:
            return outputPrefix + "###"
        elif outputName == 5:
            return outputPrefix + ".###"
        elif outputName == 6:
            return outputPrefix + ".####." + outputExtension
        
        return ""
    
    def GetExtensionFromFormat( self, outputFormat ):
        extension = ""
        
        # These values are pulled from coffeesymbols.h, which can be found in
        # the 'resource' folder in the C4D install directory.
        if outputFormat == 1102: # BMP
            extension = "bmp"
        elif outputFormat == 1109: # B3D
            extension = "b3d"
        elif outputFormat == 1023737: # DPX
            extension = "dpx"
        elif outputFormat == 1103: # IFF
            extension = "iff"
        elif outputFormat == 1104: # JPG
            extension = "jpg"
        elif outputFormat == 1016606: # openEXR
            extension = "exr"
        elif outputFormat == 1106: # PSD
            extension = "psd"
        elif outputFormat == 1111: # PSB
            extension = "psb"
        elif outputFormat == 1105: # PICT
            extension = "pct"
        elif outputFormat == 1023671: # PNG
            extension = "png"
        elif outputFormat == 1001379: # HDR
            extension = "hdr"
        elif outputFormat == 1107: # RLA
            extension = "rla"
        elif outputFormat == 1108: # RPF
            extension = "rpf"
        elif outputFormat == 1101: # TGA
            extension = "tga"
        elif outputFormat == 1110: # TIF (B3D Layers)
            extension = "tif"
        elif outputFormat == 1100: # TIF (PSD Layers)
            extension = "tif"
        elif outputFormat == 1024463: # IES
            extension = "ies"
        elif outputFormat == 1122: # AVI
            extension = "avi"
        elif outputFormat == 1125: # QT
            extension = "mov"
        elif outputFormat == 1150: # QT (Panarama)
            extension = "mov"
        elif outputFormat == 1151: # QT (object)
            extension = "mov"
        elif outputFormat == 1112363110: # QT (bmp)
            extension = "bmp"
        elif outputFormat == 1903454566: # QT (image)
            extension = "qtif"
        elif outputFormat == 1785737760: # QT (jp2)
            extension = "jp2"
        elif outputFormat == 1246774599: # QT (jpg)
            extension = "jpg"
        elif outputFormat == 943870035: # QT (photoshop)
            extension = "psd"
        elif outputFormat == 1346978644: # QT (pict)
            extension = "pct"
        elif outputFormat == 1347307366: # QT (png)
            extension = "png"
        elif outputFormat == 777209673: # QT (sgi)
            extension = "sgi"
        elif outputFormat == 1414088262: # QT (tiff)
            extension = "tif"
        
        return extension
    
    def ReadInDraftOptions(self):
        # Read in configuration files for Draft drop downs
        mainDraftFolder = os.path.join( self.DeadlineRepositoryRoot, "submission", "Draft", "Main" )
        self.Formats = self.ReadInFormatsFile( os.path.join( mainDraftFolder, "formats.txt" ) )
        self.Resolutions = self.ReadInResolutionsFile( os.path.join( mainDraftFolder, "resolutions.txt" ) )
        self.ReadInCodecsFile( os.path.join( mainDraftFolder, "codecs.txt" ) )
        self.FrameRates = self.ReadInFile( os.path.join( mainDraftFolder, "frameRates.txt" ) )
        self.Restrictions = self.ReadInRestrictionsFile( os.path.join( mainDraftFolder, "restrictions.txt" ) )
    
    def ReadInFormatsFile( self, filename ):
        results = []
        try:
            for line in open( filename ):
                words = line.split(',')
                name = words[1].strip() + " (" + words[0].strip() + ")"
                results.append( name )
                self.FormatsDict[name] = [words[0].strip(), words[2].strip()]
            results = filter( None, results )
        except:
            errorMsg = "Failed to read in configuration file " + filename
            print errorMsg
            raise Exception(errorMsg)
        return results
    
    def ReadInResolutionsFile( self, filename ):
        results = []
        try:
            for line in open( filename ):
                words = line.split(',')
                name = words[1].strip() 
                results.append( name )
                self.ResolutionsDict[name] = words[0].strip()
            results = filter( None, results )
        except:
            errorMsg = "Failed to read in configuration file " + filename
            print errorMsg
            raise Exception(errorMsg)
        return results

    def ReadInCodecsFile( self, filename ):
        try:
            for line in open( filename ):
                words = line.split( ':' )
                name = words[0].strip()
                if not name in self.CodecsDict:
                    self.CodecsDict[name] = {}

                codecList = map( str.strip, words[1].split( "," ) )
                self.CodecsDict[name] = codecList

        except:
            errorMsg = "Failed to read in configuration file " + filename + "."
            print errorMsg
            raise Exception( errorMsg )

    def ReadInRestrictionsFile( self, filename ):
        results = []
        try:
            for line in open( filename ):
                words = line.split( ':' )
                name = words[0].strip()
                restriction = words[1].split( '=' )
                restrictionType = restriction[0].strip()
                restrictionList = map( str.strip, restriction[1].split( "," ) )
                if not name in self.RestrictionsDict:
                    results.append( name )
                    self.RestrictionsDict[name] = {}
                    self.RestrictionsDict[name][restrictionType] = restrictionList
                    #RestrictionsDict[name] = [[restrictionType, restrictionList]]
                else:
                    self.RestrictionsDict[name][restrictionType] = restrictionList
                    #RestrictionsDict[name].append([restrictionType, restrictionList])
            results = filter( None, results )
        except:
            print traceback.format_exc()
            errorMsg = "Failed to read in configuration file " + filename
            print errorMsg
            raise Exception( errorMsg )
        return results
    
    def ReadInFile( self, filename ):
        try:
            results = filter( None, [line.strip() for line in open( filename )] )
        except: 
            errorMsg = "Failed to read in configuration file " + filename
            print errorMsg
            raise Exception(errorMsg)
        return results
    
    def GetOptions( self, selection, selectionType, validOptions ):
        if selection in self.RestrictionsDict:
            if selectionType in self.RestrictionsDict[selection]:
                restrictedOptions = self.RestrictionsDict[selection][selectionType]
                validOptions = list( set( validOptions ).intersection( restrictedOptions ) )
        return validOptions
    
## Class to create the submission menu item in C4D.
class SubmitC4DtoDeadlineMenu (plugins.CommandData):
    ScriptPath = ""
    
    def __init__( self, path ):
        self.ScriptPath = path
    
    def Execute( self, doc ):
        if SaveScene():
            dialog = SubmitC4DToDeadlineDialog()
            dialog.Open( c4d.DLG_TYPE_MODAL )
        return True
    
    def GetScriptName( self ):
        return "Submit To Deadline"

def CallDeadlineCommand( arguments, hideWindow=True ):
    # On OSX, we look for the DEADLINE_PATH file. On other platforms, we use the environment variable.
    if os.path.exists( "/Users/Shared/Thinkbox/DEADLINE_PATH" ):
        with open( "/Users/Shared/Thinkbox/DEADLINE_PATH" ) as f: deadlineBin = f.read().strip()
        deadlineCommand = deadlineBin + "/deadlinecommand"
    else:
        deadlineBin = os.environ['DEADLINE_PATH']
        if os.name == 'nt':
            deadlineCommand = deadlineBin + "\\deadlinecommand.exe"
        else:
            deadlineCommand = deadlineBin + "/deadlinecommand"
    
    startupinfo = None
    if hideWindow and os.name == 'nt':
        # Python 2.6 has subprocess.STARTF_USESHOWWINDOW, and Python 2.7 has subprocess._subprocess.STARTF_USESHOWWINDOW, so check for both.
        if hasattr( subprocess, '_subprocess' ) and hasattr( subprocess._subprocess, 'STARTF_USESHOWWINDOW' ):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
        elif hasattr( subprocess, 'STARTF_USESHOWWINDOW' ):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    environment = {}
    for key in os.environ.keys():
        environment[key] = str(os.environ[key])
        
    # Need to set the PATH, cuz windows seems to load DLLs from the PATH earlier that cwd....
    if os.name == 'nt':
        environment['PATH'] = str(deadlineBin + os.pathsep + os.environ['PATH'])
    
    arguments.insert( 0, deadlineCommand)
    
    # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
    proc = subprocess.Popen(arguments, cwd=deadlineBin, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo, env=environment)
    proc.stdin.close()
    proc.stderr.close()
    
    output = proc.stdout.read()
    
    return output

class TokenString(string.Template):
    idpattern = '[a-zA-Z]+'

# Iterate through objects in take (op)
def GetNextObject( op ):
    if op==None:
      return None
  
    if op.GetDown():
      return op.GetDown()
  
    while not op.GetNext() and op.GetUp():
      op = op.GetUp()
  
    return op.GetNext()    

## Global function to save the scene. Returns True if the scene has been saved and it's OK to continue.
def SaveScene():
    scene = documents.GetActiveDocument()
    
    # Save the scene if required.
    if scene.GetDocumentPath() == "" or scene.GetChanged():
        print( "Scene file needs to be saved" )
        c4d.CallCommand( 12098 ) # this is the ID for the Save command (from Command Manager)
        if scene.GetDocumentPath() == "":
            gui.MessageDialog( "The scene must be saved before it can be submitted to Deadline" )
            return False
    
    return True
    
## Global function used to register our submission script as a plugin.
def main( path ):
    pluginID = 1025665
    plugins.RegisterCommandPlugin( pluginID, "Submit To Deadline", 0, None, "Submit a Cinema 4D job to Deadline.", SubmitC4DtoDeadlineMenu( path ) )

## For debugging.
if __name__=='__main__':
    if SaveScene():
        dialog = SubmitC4DToDeadlineDialog()
        dialog.Open( c4d.DLG_TYPE_MODAL )
