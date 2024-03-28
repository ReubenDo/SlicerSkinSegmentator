import os
import logging
import vtk
import slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
import vtkSegmentationCorePython as vtkSegmentationCore
import sysconfig
import shutil
try:
   from skinsegmentator.python_api import skinsegmentator
except:
  # slicer.util.pip_install('git+https://github.com/ReubenDo/SkinSegmentator#egg=SkinSegmentator')
  slicer.util.pip_install('skinsegmentator')
  from skinsegmentator.python_api import skinsegmentator


#
# SlicerSkinSegmentator
#
REPO = 'https://github.com/ReubenDo/SlicerSlicerSkinSegmentator/'

class SlicerSkinSegmentator(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = 'Skin Surface Segmentator'
    self.parent.categories = ['Segmentation']
    self.parent.dependencies = []
    self.parent.contributors = ["Reuben Dorent (Harvard University)"]  
    self.parent.helpText = (
      'Skin surface segmentator based on SlicerSkinSegmentator.'
      f'<p>Code: <a href="{REPO}">here</a>.</p>'
    )
    # self.parent.acknowledgementText = (
    #   'This work was was funded by the Engineering and Physical Sciences'
    #   ' Research Council (EPSRC) and supported by the School of Biomedical Engineering'
    #   " & Imaging Sciences (BMEIS) of King's College London."
    # )

#
# SlicerSkinSegmentatorWidget
#
class SlicerSkinSegmentatorWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None
    self._parameterNode = None
    self._updatingGUIFromParameterNode = False

  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/SlicerSkinSegmentator.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
    # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
    # "setMRMLScene(vtkMRMLScene*)" slot.
    uiWidget.setMRMLScene(slicer.mrmlScene)

    # Create logic class. Logic implements all computations that should be possible to run
    # in batch mode, without a graphical user interface.
    self.logic = SlicerSkinSegmentatorLogic()
    self.logic.logCallback = self.addLog
    # Connections

    # These connections ensure that we update parameter node when scene is closed
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.StartCloseEvent, self.onSceneStartClose)
    self.addObserver(slicer.mrmlScene, slicer.mrmlScene.EndCloseEvent, self.onSceneEndClose)

    # These connections ensure that whenever user changes some settings on the GUI, that is saved in the MRML scene
    # (in the selected parameter node).
    self.ui.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)
    self.ui.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.updateParameterNodeFromGUI)

    # Buttons
    self.ui.applyButton.connect('clicked(bool)', self.onApplyButton)

    # Make sure parameter node is initialized (needed for module reload)
    self.initializeParameterNode()
    
  def addLog(self, text):
      """Append text to log window
      """
      self.ui.statusLabel.appendPlainText(text)
      slicer.app.processEvents()  # force update
    

  def cleanup(self):
    """
    Called when the application closes and the module widget is destroyed.
    """
    self.removeObservers()

  def enter(self):
    """
    Called each time the user opens this module.
    """
    # Make sure parameter node exists and observed
    self.initializeParameterNode()

  def exit(self):
    """
    Called each time the user opens a different module.
    """
    # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
    self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

  def onSceneStartClose(self, caller, event):
    """
    Called just before the scene is closed.
    """
    # Parameter node will be reset, do not use it anymore
    self.setParameterNode(None)

  def onSceneEndClose(self, caller, event):
    """
    Called just after the scene is closed.
    """
    # If this module is shown while the scene is closed then recreate a new parameter node immediately
    if self.parent.isEntered:
      self.initializeParameterNode()

  def initializeParameterNode(self):
    """
    Ensure parameter node exists and observed.
    """
    # Parameter node stores all user choices in parameter values, node selections, etc.
    # so that when the scene is saved and reloaded, these settings are restored.

    self.setParameterNode(self.logic.getParameterNode())

    # Select default input nodes if nothing is selected yet to save a few clicks for the user
    if not self._parameterNode.GetNodeReference("InputVolume"):
      firstVolumeNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLScalarVolumeNode")
      if firstVolumeNode:
        self._parameterNode.SetNodeReferenceID("InputVolume", firstVolumeNode.GetID())

  def setParameterNode(self, inputParameterNode):
    """
    Set and observe parameter node.
    Observation is needed because when the parameter node is changed then the GUI must be updated immediately.
    """

    if inputParameterNode:
      self.logic.setDefaultParameters(inputParameterNode)

    # Unobserve previously selected parameter node and add an observer to the newly selected.
    # Changes of parameter node are observed so that whenever parameters are changed by a script or any other module
    # those are reflected immediately in the GUI.
    if self._parameterNode is not None:
      self.removeObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)
    self._parameterNode = inputParameterNode
    if self._parameterNode is not None:
      self.addObserver(self._parameterNode, vtk.vtkCommand.ModifiedEvent, self.updateGUIFromParameterNode)

    # Initial GUI update
    self.updateGUIFromParameterNode()

  def updateGUIFromParameterNode(self, caller=None, event=None):
    """
    This method is called whenever parameter node is changed.
    The module GUI is updated to show the current state of the parameter node.
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    # Make sure GUI changes do not call updateParameterNodeFromGUI (it could cause infinite loop)
    self._updatingGUIFromParameterNode = True

    # Update node selectors and sliders
    self.ui.inputSelector.setCurrentNode(self._parameterNode.GetNodeReference("InputVolume"))
    self.ui.outputSelector.setCurrentNode(self._parameterNode.GetNodeReference("OutputVolume"))
    #self.ui.progressBar1.setCurrentNode(self._parameterNode.GetNodeReference("ProgressBar1"))

    # Update buttons states and tooltips
    if self._parameterNode.GetNodeReference("InputVolume") and self._parameterNode.GetNodeReference("OutputVolume"):
      self.ui.applyButton.toolTip = "Compute output volume"
      self.ui.applyButton.enabled = True
    else:
      self.ui.applyButton.toolTip = "Select input and output volume nodes"
      self.ui.applyButton.enabled = False

    # All the GUI updates are done
    self._updatingGUIFromParameterNode = False

  def updateParameterNodeFromGUI(self, caller=None, event=None):
    """
    This method is called when the user makes any change in the GUI.
    The changes are saved into the parameter node (so that they are restored when the scene is saved and loaded).
    """

    if self._parameterNode is None or self._updatingGUIFromParameterNode:
      return

    wasModified = self._parameterNode.StartModify()  # Modify all properties in a single batch

    self._parameterNode.SetNodeReferenceID("InputVolume", self.ui.inputSelector.currentNodeID)
    self._parameterNode.SetNodeReferenceID("OutputVolume", self.ui.outputSelector.currentNodeID)

    self._parameterNode.EndModify(wasModified)

  def onApplyButton(self):
    """
    Run processing when user clicks "Apply" button.
    """
    try:
      # Compute output
      self.logic.process(self.ui.inputSelector.currentNode(), self.ui.outputSelector.currentNode())

    except Exception as e:
      slicer.util.errorDisplay("Failed to compute results: "+str(e))
      import traceback
      traceback.print_exc()


#
# SlicerSkinSegmentatorLogic
#

class SlicerSkinSegmentatorLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)
    self.logCallback = None
    

  def log(self, text):
      logging.info(text)
      if self.logCallback:
          self.logCallback(text)
  
  def logProcessOutput(self, proc, returnOutput=False):
      # Wait for the process to end and forward output to the log
      output = ""
      from subprocess import CalledProcessError
      while True:
          try:
              line = proc.stdout.readline()
              if not line:
                  break
              if returnOutput:
                  output += line
              self.log(line.rstrip())
          except UnicodeDecodeError as e:
              # Code page conversion happens because `universal_newlines=True` sets process output to text mode,
              # and it fails because probably system locale is not UTF8. We just ignore the error and discard the string,
              # as we only guarantee correct behavior if an UTF8 locale is used.
              pass

      proc.wait()
      retcode = proc.returncode
      if retcode != 0:
          raise CalledProcessError(retcode, proc.args, output=proc.stdout, stderr=proc.stderr)
      return output if returnOutput else None

  def setDefaultParameters(self, parameterNode):
    """
    Initialize parameter node with default settings.
    """
    pass
          
  def readSegmentation(self, outputSegmentation, outputSegmentationFile, task='skin'):

    # Get label descriptions
    from skinsegmentator.map_to_binary import class_map
    labelValueToSegmentName = class_map[task]
    maxLabelValue = max(labelValueToSegmentName.keys())
    if min(labelValueToSegmentName.keys()) < 0:
        raise RuntimeError("Label values in class_map must be positive")

    # Get color node with random colors
    randomColorsNode = slicer.mrmlScene.GetNodeByID('vtkMRMLColorTableNodeRandom')
    rgba = [0, 0, 0, 0]

    # Create color table for this segmentation task
    colorTableNode = slicer.vtkMRMLColorTableNode()
    colorTableNode.SetTypeToUser()
    colorTableNode.SetNumberOfColors(maxLabelValue+1)
    colorTableNode.SetName(task)
    for labelValue in labelValueToSegmentName:
        randomColorsNode.GetColor(labelValue,rgba)
        colorTableNode.SetColor(labelValue, rgba[0], rgba[1], rgba[2], rgba[3])
        colorTableNode.SetColorName(labelValue, labelValueToSegmentName[labelValue])
    slicer.mrmlScene.AddNode(colorTableNode)

    # Load the segmentation
    # outputSegmentation.SetLabelmapConversionColorTableNodeID(colorTableNode.GetID())
    outputSegmentation.AddDefaultStorageNode()
    storageNode = outputSegmentation.GetStorageNode()
    storageNode.SetFileName(outputSegmentationFile)
    storageNode.ReadData(outputSegmentation)

    slicer.mrmlScene.RemoveNode(colorTableNode)


  def process(self, inputVolume, outputVolume):
    """
    Run the processing algorithm.
    Can be used without GUI widget.
    :param inputVolume: volume to be thresholded
    :param outputVolume: thresholding result
    """

    if not inputVolume or not outputVolume:
      raise ValueError("Input or output volume is invalid")
    
    import time
    startTime = time.time()
    self.log('Processing started')
    
    tempFolder = slicer.util.tempDirectory()
    
    
    inputFile = tempFolder+"/skin-segmentator-input.nii.gz"
    # print (outputSegmentationFolder)
    outputSegmentationFile = tempFolder + "/skin.nii.gz"

    # Recommend the user to switch to fast mode if no GPU or not enough memory is available
    import torch

    cuda = torch.cuda if torch.backends.cuda.is_built() and torch.cuda.is_available() else None

    # Get SkinSegmentator launcher command
    # SkinSegmentator (.py file, without extension) is installed in Python Scripts folder
    
    if os.name == 'nt':
      SkinSegmentatorExecutablePath = os.path.join(sysconfig.get_path('scripts'), "SkinSegmentator.exe")
    else:
      SkinSegmentatorExecutablePath = os.path.join(sysconfig.get_path('scripts'), "SkinSegmentator")
    # Get Python executable path
    
    pythonSlicerExecutablePath = shutil.which('PythonSlicer')
    if not pythonSlicerExecutablePath:
        raise RuntimeError("Python was not found")
    SkinSegmentatorCommand = [ pythonSlicerExecutablePath, SkinSegmentatorExecutablePath]

    # Write input volume to file
    # SkinSegmentator requires NIFTI
    self.log(f"Writing input file to {inputFile}")
    volumeStorageNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLVolumeArchetypeStorageNode")
    volumeStorageNode.SetFileName(inputFile)
    volumeStorageNode.UseCompressionOff()
    volumeStorageNode.WriteData(inputVolume)
    volumeStorageNode.UnRegister(None)

    # Get options
    options = ["-i", inputFile, "-o", outputSegmentationFile]
    self.log('Creating segmentations with SkinSegmentator...')
    self.log(f"Skin Segmentator arguments: {options}")
    proc = slicer.util.launchConsoleProcess(SkinSegmentatorCommand + options)
    self.logProcessOutput(proc)

    # Load result
    self.log('Importing segmentation results...')

    # Create output labelmap
    labelmapVolumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    self.readSegmentation(labelmapVolumeNode, outputSegmentationFile)
    
    self.log("Cleaning up temporary folder...")
    if os.path.isdir(tempFolder):
        shutil.rmtree(tempFolder)
    
    # Place segmentation node in the same place as the input volume
    shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
    inputVolumeShItem = shNode.GetItemByDataNode(inputVolume)
    studyShItem = shNode.GetItemParent(inputVolumeShItem)
    segmentationShItem = shNode.GetItemByDataNode(labelmapVolumeNode)
    shNode.SetItemParent(segmentationShItem, studyShItem)

    # Create surface
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, outputVolume)
    outputVolume.CreateClosedSurfaceRepresentation()
    slicer.mrmlScene.RemoveNode(labelmapVolumeNode)

    segmentation = vtkSegmentationCore.vtkSegmentation()
    # Turn of surface smoothing
    segmentation.SetConversionParameter("Smoothing factor","1.0")

    # Recreate representation using modified parameters (and default conversion path)
    segmentation.RemoveRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName())
    segmentation.CreateRepresentation(vtkSegmentationCore.vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName())
    
    stopTime = time.time()
    self.log(f'Processing completed in {stopTime-startTime:.2f} seconds')

#
# SlicerSkinSegmentatorTest
#

class SlicerSkinSegmentatorTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_SlicerSlicerSkinSegmentator1()

  def test_SlicerSlicerSkinSegmentator1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    # registerSampleData()
    inputVolume = SampleData.downloadSample('MRBrainTumor1')
    self.delayDisplay('Loaded test data set')

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")

    # Test the module logic

    logic = SlicerSkinSegmentatorLogic()

    # Test algorithm 
    logic.process(inputVolume, outputVolume)

    self.delayDisplay('Test passed')
