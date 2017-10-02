from PySide2.QtWidgets import QUndoCommand, QUndoStack
from PySide2.QtCore import Property, Signal
from meshroom.processGraph.graph import Node


class UndoCommand(QUndoCommand):
    def __init__(self, parent=None):
        super(UndoCommand, self).__init__(parent)
        self._enabled = True

    def setEnabled(self, enabled):
        self._enabled = enabled

    def redo(self):
        if not self._enabled:
            return
        self.redoImpl()

    def undo(self):
        if not self._enabled:
            return
        self.undoImpl()

    def redoImpl(self) -> bool:
        pass

    def undoImpl(self) -> bool:
        pass


class UndoStack(QUndoStack):
    def __init__(self, parent=None):
        super(UndoStack, self).__init__(parent)
        # connect QUndoStack signal to UndoStack's ones
        self.cleanChanged.connect(self._cleanChanged)
        self.canUndoChanged.connect(self._canUndoChanged)
        self.canRedoChanged.connect(self._canRedoChanged)
        self.undoTextChanged.connect(self._undoTextChanged)
        self.redoTextChanged.connect(self._redoTextChanged)

    def tryAndPush(self, command: UndoCommand):
        if command.redoImpl():
            command.setEnabled(False)
            self.push(command)  # takes ownership
            command.setEnabled(True)
            return True
        else:
            return False

    # Redeclare QUndoStack signal since original ones can not be used for properties notifying
    _cleanChanged = Signal()
    _canUndoChanged = Signal()
    _canRedoChanged = Signal()
    _undoTextChanged = Signal()
    _redoTextChanged = Signal()

    clean = Property(bool, QUndoStack.isClean, notify=_cleanChanged)
    canUndo = Property(bool, QUndoStack.canUndo, notify=_canRedoChanged)
    canRedo = Property(bool, QUndoStack.canRedo, notify=_canUndoChanged)
    undoText = Property(str, QUndoStack.undoText, notify=_undoTextChanged)
    redoText = Property(str, QUndoStack.redoText, notify=_redoTextChanged)


class GraphCommand(UndoCommand):
    def __init__(self, graph, parent=None):
        super(GraphCommand, self).__init__(parent)
        self.graph = graph


class AddNodeCommand(GraphCommand):
    def __init__(self, graph, nodeType, parent=None):
        super(AddNodeCommand, self).__init__(graph, parent)
        self.nodeType = nodeType
        self.node = None

    def redoImpl(self):
        self.node = self.graph.addNewNode(self.nodeType)
        self.setText("Add Node {}".format(self.node.getName()))
        return True

    def undoImpl(self):
        self.graph.removeNode(self.node.getName())
        self.node = None


class RemoveNodeCommand(GraphCommand):
    def __init__(self, graph, node, parent=None):
        super(RemoveNodeCommand, self).__init__(graph, parent)
        self.nodeDesc = node.toDict()
        self.nodeName = node.getName()
        self.setText("Remove Node {}".format(self.nodeName))

    def redoImpl(self):
        self.graph.removeNode(self.nodeName)
        return True

    def undoImpl(self):
        node = self.graph.addNode(Node(nodeDesc=self.nodeDesc["nodeType"],
                                       parent=self.graph, **self.nodeDesc["attributes"]
                                       ), self.nodeName)
        assert (node.getName() == self.nodeName)


class SetAttributeCommand(GraphCommand):
    def __init__(self, graph, attribute, value, parent=None):
        super(SetAttributeCommand, self).__init__(graph, parent)
        self.nodeName = attribute.node.getName()
        self.attrName = attribute.getName()
        self.value = value
        self.oldValue = attribute.getValue()

    def redoImpl(self):
        self.graph.node(self.nodeName).attribute(self.attrName).setValue(self.value)
        return True

    def undoImpl(self):
        self.graph.node(self.nodeName).attribute(self.attrName).setValue(self.oldValue)