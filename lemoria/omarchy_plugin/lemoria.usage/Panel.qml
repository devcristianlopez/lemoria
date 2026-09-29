import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

// Lemoria's own usage widget.
//
// The omarchy.agents panel has nowhere to put an all-time token total or the
// model an agent runs on, and that contract is Omarchy's to widen, not ours.
// So this reads the same record and draws the parts the record actually has.
//
// Everything shown here is already computed by `lemoria omarchy record`. The
// plugin does no arithmetic beyond formatting, which is why it needs no Python.
Panel {
  id: root
  moduleName: "lemoria.usage"
  ipcTarget: "lemoria.usage"
  manageIpc: false

  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color urgent: bar ? bar.urgent : Color.urgent
  readonly property color dim: Qt.darker(foreground, 1.55)
  readonly property color surface: Color.popups.background
  readonly property color track: Style.selectedFillFor(foreground, Color.accent)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  // Make the gap part of the clickable/rendered item itself. BarIconButton is
  // intentionally a fixed icon slot, so adding a sibling spacer can still look
  // collapsed in the shell row; WidgetButton sizes from its text plus margins.
  readonly property real textMargin: 11.5

  readonly property string stateHome: Quickshell.env("XDG_STATE_HOME")
    || (Quickshell.env("HOME") + "/.local/state")
  readonly property string recordPath: root.stateHome + "/lemoria/omarchy/usage.json"

  // Same ladder the collector uses: green under 80%, amber approaching, red
  // past. Amber is the one that matters -- it is the warning you can still act
  // on instead of reading about a budget that is already gone.
  readonly property color budgetColor: !usage.budgeted ? dim
    : root.budget.status === "over" ? urgent
    : root.budget.status === "warn" ? Style.selectedFillFor(foreground, Color.urgent)
    : foreground

  // 293M, 1.2B. Precise enough to act on, short enough for a bar.
  function compact(n) {
    if (!n) return "0"
    if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + "B"
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + "M"
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K"
    return String(n)
  }

  function pct(part, whole) {
    if (!whole) return 0
    return Math.max(0, Math.min(1, part / whole))
  }

  Record {
    id: usage
    path: root.recordPath
  }

  readonly property var record: usage.record || ({})
  readonly property var budget: usage.budget || ({
    funded: null, used: 0, remaining: null, percent: null, status: "unset"
  })
  readonly property var recentDays: Array.isArray(root.record.recentDays) ? root.record.recentDays : []
  readonly property int recentMax: {
    var max = 1
    for (var i = 0; i < root.recentDays.length; i++)
      max = Math.max(max, Number(root.recentDays[i].messageCount || 0))
    return max
  }

  // Bar.qml sizes a plugin slot from the root item's implicit size. Without
  // this contract the widget is registered and present in shell.json, but its
  // slot collapses to 0x0 and the user sees no Lemoria panel.
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.left: parent.left
    anchors.verticalCenter: parent.verticalCenter
    width: root.width > 0 ? root.width : implicitWidth
    height: root.height > 0 ? root.height : implicitHeight
    bar: root.bar
    fontSize: Style.bar.iconFont
    horizontalMargin: root.textMargin
    // The all-time total, always on the bar. It is the number the user asked
    // to see without clicking anything, so it never hides.
    text: usage.hasUsage ? root.compact(root.record.totalTokens) : "0"
    active: usage.alarming
    useActiveColor: true
    onPressed: function(buttonCode) {
      if (buttonCode === Qt.MiddleButton) root.toggle()
      else if (buttonCode === Qt.RightButton) {
        if (root.bar) root.bar.run("lemoria usage")
      } else root.toggle()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(430))
    contentHeight: panel.fittedContentHeight(column.implicitHeight, Style.space(620))

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onActivateRequested: if (root.bar) root.bar.run("lemoria usage")
    }

    Flickable {
      id: flick
      anchors.fill: parent
      contentWidth: width
      contentHeight: column.implicitHeight
      clip: true
      boundsBehavior: Flickable.StopAtBounds
      flickableDirection: Flickable.VerticalFlick
      interactive: contentHeight > height
      ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

      Column {
        id: column
        width: flick.width
        spacing: Style.space(12)

        // --------------------------------------------------------- empty state
        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: !usage.hasUsage

          PanelSectionHeader {
            width: parent.width
            text: "Lemoria usage"
          }

          Text {
            width: parent.width
            text: root.record.authHelpText || "Waiting for opencode usage data."
            color: root.dim
            font.family: root.fontFamily
            font.pixelSize: Style.font.body
            wrapMode: Text.WordWrap
          }
        }

        // ---------------------------------------------------- all-time total
        PanelHero {
          width: parent.width
          visible: usage.hasUsage
          title: root.compact(root.record.totalTokens) + " tokens"
          meta: root.record.activeDates && root.record.activeDates.length > 1
            ? root.record.activeDates[0] + " → " + root.record.activeDates[root.record.activeDates.length - 1]
            : (root.record.activeDays + " active days")
          detail: root.record.totalSessions + " sessions · " + root.record.totalPrompts + " prompts"
        }

        // -------------------------------------------------------------- today
        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: usage.hasUsage

          PanelSectionHeader {
            width: parent.width
            text: "Today"
          }

          Row {
            width: parent.width
            spacing: Style.space(8)

            Text {
              text: root.compact(root.record.todayTotalTokens) + " tokens"
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.subtitle
            }
            Text {
              text: "· " + root.record.todaySessions + (root.record.todaySessions === 1 ? " session" : " sessions")
                + " · " + root.record.todayPrompts + " prompts"
              color: root.dim
              font.family: root.fontFamily
              font.pixelSize: Style.font.body
              anchors.baseline: parent.children[0].baseline
            }
          }
        }

        // --------------------------------------------------------- seven days
        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: usage.hasUsage && root.recentDays.length > 0

          PanelSectionHeader {
            width: parent.width
            text: "Last 7 days"
          }

          Repeater {
            model: root.recentDays

            delegate: Row {
              required property var modelData
              width: column.width
              spacing: Style.space(8)

              Text {
                width: Style.space(76)
                text: String(modelData.date || "")
                color: root.dim
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
              }

              Rectangle {
                width: Math.max(Style.space(4), (column.width - Style.space(150))
                                * root.pct(Number(modelData.messageCount || 0), root.recentMax))
                height: Style.space(7)
                radius: height / 2
                color: root.foreground
                anchors.verticalCenter: parent.verticalCenter
              }

              Text {
                text: root.compact(Number(modelData.messageCount || 0))
                color: root.dim
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
                anchors.verticalCenter: parent.verticalCenter
              }
            }
          }
        }

        // ------------------------------------------------------- budget meter
        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: usage.budgeted

          PanelSectionHeader {
            width: parent.width
            text: "Monthly budget"
          }

          Text {
            text: root.compact(root.budget.used) + " of " + root.compact(root.budget.funded) + " tokens"
              + "  ·  " + root.budget.percent + "%"
            color: root.budgetColor
            font.family: root.fontFamily
            font.pixelSize: Style.font.body
          }

          // The bar itself: spent on top, room left underneath. Past the limit
          // the fill just stops at the edge -- `remaining` can be negative and
          // a negative width would draw backwards.
          Rectangle {
            id: budgetTrack
            width: parent.width
            height: Style.space(8)
            radius: height / 2
            color: Qt.darker(root.surface, 1.0)

            Rectangle {
              width: budgetTrack.width * root.pct(root.budget.used, root.budget.funded)
              height: parent.height
              radius: height / 2
              color: root.budgetColor
              Behavior on width { NumberAnimation { duration: 180 } }
            }
          }

          Text {
            text: root.budget.status === "over"
              ? root.compact(-root.budget.remaining) + " over budget"
              : root.compact(root.budget.remaining) + " left"
            color: root.dim
            font.family: root.fontFamily
            font.pixelSize: Style.font.bodySmall
          }
        }

        PanelSeparator {
          width: parent.width
          visible: usage.agents.length > 0
        }

        // ------------------------------------------------------- per agent
        //
        // The reason this panel exists. omarchy.agents has no field for it.
        Column {
          width: parent.width
          spacing: Style.space(6)
          visible: usage.agents.length > 0

          PanelSectionHeader {
            width: parent.width
            text: "By agent · consolidated"
          }

          Text {
            width: parent.width
            text: "Totals include every model/provider an agent used; model is current/configured. Observed usage is noted separately."
            color: root.dim
            font.family: root.fontFamily
            font.pixelSize: Style.font.caption
            wrapMode: Text.WordWrap
          }

          Row {
            width: parent.width
            spacing: Style.space(6)

            Text { width: parent.width * 0.42; text: "agent"; color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.caption }
            Text { width: parent.width * 0.24; text: "total"; color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.caption; horizontalAlignment: Text.AlignRight }
            Text { width: parent.width * 0.18; text: "today"; color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.caption; horizontalAlignment: Text.AlignRight }
            Text { width: parent.width * 0.16; text: "share"; color: root.dim; font.family: root.fontFamily; font.pixelSize: Style.font.caption; horizontalAlignment: Text.AlignRight }
          }

          Repeater {
            model: usage.agents

            delegate: Column {
              id: row
              required property var modelData
              width: column.width
              spacing: Style.space(1)

              readonly property var entry: modelData
              readonly property int share: root.record.totalTokens
                ? Math.round((entry.tokens / root.record.totalTokens) * 100) : 0
              readonly property string configuredModel: entry.model ? String(entry.model) : ""
              readonly property string observedModel: entry.observedModel ? String(entry.observedModel) : ""
              readonly property bool hasObservedModel: observedModel.length > 0
              readonly property bool observedDiffers: hasObservedModel && observedModel !== configuredModel
              readonly property string headlineModel: shortModel(configuredModel)
              readonly property int modelCount: entry.models ? Object.keys(entry.models).length : 0
              readonly property int observedTokens: hasObservedModel && entry.models
                ? Number(entry.models[observedModel] || 0) : 0
              readonly property int observedShare: entry.tokens && observedTokens
                ? Math.round((observedTokens / entry.tokens) * 100) : 0

              function shortModel(modelName) {
                return modelName ? String(modelName).split("/").pop() : "—"
              }

              function observedSummary() {
                if (!hasObservedModel || !entry.tokens) return ""

                var pieces = []
                if (observedShare > 0) pieces.push(observedShare + "%")
                if (modelCount > 1) pieces.push("+" + (modelCount - 1) + " more")
                if (pieces.length === 0) return ""

                return "(" + pieces.join(", ") + ")"
              }

              Row {
                width: parent.width
                spacing: Style.space(6)

                Text {
                  width: row.width * 0.42
                  text: row.entry.agent
                  color: root.foreground
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                  elide: Text.ElideRight
                }
                Text {
                  width: row.width * 0.24
                  text: root.compact(row.entry.tokens)
                  color: root.foreground
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.body
                  horizontalAlignment: Text.AlignRight
                }
                Text {
                  width: row.width * 0.18
                  text: row.entry.todayTokens > 0 ? "+" + root.compact(row.entry.todayTokens) : "—"
                  color: row.entry.todayTokens > 0 ? root.dim : Qt.darker(root.dim, 1.4)
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                  horizontalAlignment: Text.AlignRight
                }
                Text {
                  width: row.width * 0.16
                  text: row.share + "%"
                  color: root.dim
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                  horizontalAlignment: Text.AlignRight
                }
              }

              // Model details, on their own line. The headline is the current
              // configured/default model. Historical shares come from observed
              // usage only; if that differs, keep it separate instead of
              // implying the configured model produced those tokens.
              Row {
                width: parent.width
                spacing: Style.space(6)
                leftPadding: row.width * 0.42 + Style.space(6)

                Text {
                  text: row.headlineModel
                  color: root.dim
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                }
                Text {
                  visible: !row.observedDiffers && row.observedSummary().length > 0
                  text: row.observedSummary()
                  color: Qt.darker(root.dim, 1.3)
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                }
                Text {
                  visible: row.observedDiffers
                  text: "obs " + row.shortModel(row.observedModel)
                    + (row.observedSummary().length > 0 ? " " + row.observedSummary() : "")
                  color: Qt.darker(root.dim, 1.3)
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.bodySmall
                }
                Text {
                  text: row.entry.sessions + (row.entry.sessions === 1 ? " session" : " sessions")
                    + " · " + row.entry.prompts + " prompts"
                  color: Qt.darker(root.dim, 1.5)
                  font.family: root.fontFamily
                  font.pixelSize: Style.font.caption
                  anchors.verticalCenter: parent.verticalCenter
                }
              }
            }
          }
        }
      }
    }
  }
}
