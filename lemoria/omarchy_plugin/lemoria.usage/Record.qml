import QtQuick
import Quickshell.Io

// The record Lemoria's collector writes, read exactly the way Omarchy's own
// Agent.qml reads one: a watcher on a JSON file in the usage directory. The
// panel never learns how the numbers were made, and a file that is missing or
// half-written simply reads as "nothing to show" rather than as an error.
Item {
  id: root
  visible: false

  property string path: ""
  property var record: null

  FileView {
    path: root.path
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.parse(text())
    onLoadFailed: root.record = null
  }

  function parse(content) {
    try {
      var parsed = JSON.parse(String(content || ""))
      root.record = parsed && typeof parsed === "object" ? parsed : null
    } catch (e) {
      // A torn read is normal: the collector writes atomically, but a panel
      // that hard-fails on one bad frame would blink itself off the bar.
      console.warn("lemoria.usage", "Ignoring bad usage record", root.path, e)
      root.record = null
    }
  }

  readonly property bool hasUsage: !!record && !!record.ready
  readonly property var agents: (record && Array.isArray(record.agents)) ? record.agents : []
  readonly property var budget: (record && record.budget) ? record.budget : null
  readonly property bool budgeted: !!(budget && budget.funded)
  readonly property bool alarming: budgeted && (budget.status === "warn" || budget.status === "over")
}
