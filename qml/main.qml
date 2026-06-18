import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Particles

ApplicationWindow {
    id: root
    visible: true
    width: 520; height: 880
    minimumWidth: 520; minimumHeight: 880
    maximumWidth: 520; maximumHeight: 880
    title: backend.tr("AI 翻譯", backend.uiLang) + " v1.0"
    color: "#040b16"

    // ── 核心背景與特效層 ──
    Image {
        id: bgImage
        anchors.fill: parent
        source: "../assets/bg_main.png"
        fillMode: Image.Tile
    }
    
    ParticleSystem {
        id: particles
        anchors.fill: parent
        
        ImageParticle {
            source: "../assets/particle.png"
            colorVariation: 0.1
        }
        
        Emitter {
            width: parent.width
            height: parent.height
            emitRate: 20
            lifeSpan: 4000
            size: 8
            sizeVariation: 4
            velocity: PointDirection { y: -20; yVariation: 10; xVariation: 5 }
        }
        
        ImageParticle {
            groups: ["meteor"]
            source: "../assets/meteor.png"
            color: Qt.rgba(0.5, 1, 1, 0.5)
        }
        
        Emitter {
            group: "meteor"
            width: parent.width
            height: 0
            emitRate: 0.2
            lifeSpan: 3000
            size: 64
            velocity: PointDirection { x: 100; y: 150; xVariation: 50; yVariation: 50 }
        }
    }
    
    Image {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        height: 200
        source: "../assets/hud_lines.png"
        fillMode: Image.TileHorizontally
        opacity: 0.5
    }

    // ── 色彩常數 ──
    readonly property color cBg:       "#040b16"
    readonly property color cCard:     "#0d1a2f"
    readonly property color cCyan:     "#00f3ff"
    readonly property color cGold:     "#ffd700"
    readonly property color cRed:      "#ff3366"
    readonly property color cGreen:    "#a6e3a1"
    readonly property color cBlue:     "#89b4fa"
    readonly property color cText:     "#ffffff"
    readonly property color cSubtext:  "#8899bb"
    readonly property color cInactive: "#1a2a42"

    property bool isRecordCancelActive: false

    Timer {
        id: delayRecordCancelTimer
        interval: 120
        repeat: false
        onTriggered: root.isRecordCancelActive = true
    }

    Connections {
        target: backend
        function onIsRecordingChanged() {
            if (backend.isRecording) {
                delayRecordCancelTimer.restart()
            } else {
                delayRecordCancelTimer.stop()
                root.isRecordCancelActive = false
            }
        }
    }

    // ── 外框與主排版 ──
    Rectangle {
        anchors.fill: parent
        anchors.margins: 10
        color: "transparent"
        border.color: cCyan
        border.width: 2
        radius: 12

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 20
            spacing: 12

            // ════════════════════════════════════
            // 標題
            // ════════════════════════════════════
            RowLayout {
                Layout.leftMargin: 10
                spacing: 10
                Image {
                    source: "../assets/logo_ai.png"
                    sourceSize: Qt.size(32, 32)
                    Layout.preferredWidth: 32; Layout.preferredHeight: 32
                }
                Text {
                    text: backend.tr("AI 翻譯", backend.uiLang)
                    font { family: "Microsoft JhengHei"; pixelSize: 22; bold: true }
                    color: cText
                }
                Text {
                    text: "v1.0"
                    font { family: "Consolas"; pixelSize: 13 }
                    color: cCyan
                    Layout.alignment: Qt.AlignBottom
                }
                Item { Layout.fillWidth: true }
                
                ComboBox {
                    id: uiLangCombo
                    Layout.preferredWidth: 210
                    Layout.preferredHeight: 32
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    model: backend.supportedLanguages
                    currentIndex: {
                        var idx = backend.supportedLanguages.indexOf(backend.uiLang);
                        return idx >= 0 ? idx : 0;
                    }
                    onActivated: backend.uiLang = currentText
                    
                    background: Rectangle {
                        color: "#0a1225"; radius: 6
                        border.color: Qt.rgba(0, 0.95, 1, 0.25); border.width: 1
                    }
                    contentItem: Text {
                        text: uiLangCombo.displayText
                        font { family: "Microsoft JhengHei"; pixelSize: 12 }
                        color: cCyan
                        verticalAlignment: Text.AlignVCenter
                        leftPadding: 8
                    }
                    indicator: Text {
                        text: "▾"
                        color: cCyan
                        font.pixelSize: 14
                        anchors { right: parent.right; rightMargin: 8; verticalCenter: parent.verticalCenter }
                    }
                    popup: Popup {
                        y: uiLangCombo.height
                        width: uiLangCombo.width
                        implicitHeight: contentItem.implicitHeight
                        padding: 1
                        contentItem: ListView {
                            clip: true
                            implicitHeight: contentHeight
                            model: uiLangCombo.popup.visible ? uiLangCombo.delegateModel : null
                            ScrollIndicator.vertical: ScrollIndicator {}
                        }
                        background: Rectangle { color: "#0a1225"; radius: 6; border.color: cCyan; border.width: 1 }
                    }
                    delegate: ItemDelegate {
                        width: uiLangCombo.width
                        contentItem: Text {
                            text: modelData
                            color: highlighted ? cGold : cText
                            font { family: "Microsoft JhengHei"; pixelSize: 12 }
                            verticalAlignment: Text.AlignVCenter
                        }
                        highlighted: uiLangCombo.highlightedIndex === index
                        background: Rectangle {
                            color: highlighted ? Qt.rgba(1, 0.84, 0, 0.1) : "transparent"
                        }
                    }
                }
            }

            // ════════════════════════════════════
            // 硬體模式
            // ════════════════════════════════════
            Item { Layout.fillHeight: true }
            SectionLabel { label: backend.tr("硬體模式", backend.uiLang) }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 10; Layout.rightMargin: 10
                spacing: 12

                HwCard {
                    text: backend.tr("🖥 CPU", backend.uiLang)
                    isActive: backend.hardware === "cpu"
                    Layout.preferredWidth: 120; Layout.preferredHeight: 50
                    onClicked: backend.hardware = "cpu"
                }
                HwCard {
                    text: backend.tr("⚡ GPU (CUDA)", backend.uiLang)
                    isActive: backend.hardware === "gpu"
                    Layout.fillWidth: true; Layout.preferredHeight: 50
                    onClicked: backend.hardware = "gpu"
                }
            }

            // ════════════════════════════════════
            // 語言設定
            // ════════════════════════════════════
            Item { Layout.fillHeight: true }
            SectionLabel { label: backend.tr("語言設定", backend.uiLang) }

            BorderImage {
                Layout.fillWidth: true
                Layout.leftMargin: 10; Layout.rightMargin: 10
                Layout.preferredHeight: langCol.implicitHeight + 24
                Layout.maximumHeight: langCol.implicitHeight + 24
                source: "../assets/panel_large.png"
                border.left: 20; border.top: 20; border.right: 20; border.bottom: 20

                ColumnLayout {
                    id: langCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                    spacing: 10

                    SettingRow {
                        label: backend.tr("翻譯引擎", backend.uiLang)
                        model: ["Google 翻譯", "Gemini 翻譯", "Qwen 2.5 72B (OpenRouter) 繁體", "Qwen 2.5 72B (OpenRouter) 簡體"]
                        currentValue: backend.engine
                        onValueChanged: (v) => {
                            backend.engine = v
                        }
                    }
                    SettingRow {
                        label: backend.tr("來源語言", backend.uiLang)
                        model: backend.supportedLanguages
                        currentValue: backend.srcLang
                        onValueChanged: (v) => backend.srcLang = v
                    }
                    SettingRow {
                        label: backend.tr("目標語言", backend.uiLang)
                        model: backend.supportedLanguages
                        currentValue: backend.tgtLang
                        onValueChanged: (v) => backend.tgtLang = v
                    }
                    
                    // OpenRouter API Key Input
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        visible: backend.engine.indexOf("Qwen") !== -1
                        Text {
                            text: "OpenRouter Key:"
                            color: cText
                            font { family: "Microsoft JhengHei"; pixelSize: 12 }
                            Layout.preferredWidth: 100
                        }
                        TextField {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 30
                            text: backend.openRouterKey
                            onTextEdited: backend.openRouterKey = text
                            placeholderText: "sk-or-v1-..."
                            passwordCharacter: "•"
                            echoMode: TextInput.PasswordEchoOnEdit
                            color: cCyan
                            font { family: "Consolas"; pixelSize: 12 }
                            background: Rectangle {
                                color: "#0a1225"
                                radius: 4
                                border.color: Qt.rgba(0, 0.95, 1, 0.3)
                            }
                        }
                    }
                }
            }

            // ════════════════════════════════════
            // 截圖快捷鍵
            // ════════════════════════════════════
            Item { Layout.fillHeight: true }
            SectionLabel { label: backend.tr("截圖快捷鍵", backend.uiLang) }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 10; Layout.rightMargin: 10
                spacing: 8

                Item {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 44
                    Layout.maximumHeight: 44

                    BorderImage {
                        anchors.fill: parent
                        source: "../assets/panel_small.png"
                        border.left: 10; border.top: 10; border.right: 10; border.bottom: 10
                        visible: !backend.isRecording
                    }

                    Rectangle {
                        anchors.fill: parent
                        color: Qt.rgba(0.1, 0.1, 0.1, 0.8)
                        radius: 22
                        border.color: cGold
                        border.width: 1
                        visible: backend.isRecording
                    }

                    Text {
                        anchors.centerIn: parent
                        text: backend.isRecording ? backend.tr("按鍵偵測中...", backend.uiLang) : backend.hotkeyDisplay
                        font { family: "Consolas"; pixelSize: 14; bold: true }
                        color: backend.isRecording ? cGold : cCyan
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (!backend.isRecording) {
                                backend.startInteractiveRecord()
                            }
                        }
                    }
                }

                NeonButton {
                    text: backend.tr("錄製", backend.uiLang)
                    iconSrc: "../assets/icon_record.png"
                    bgSrc: "../assets/btn_blue.png"
                    Layout.preferredWidth: 80; Layout.preferredHeight: 44
                    onClicked: {
                        if (!backend.isRecording) {
                            backend.startInteractiveRecord()
                        }
                    }
                }
                NeonButton {
                    text: backend.tr("重置", backend.uiLang)
                    iconSrc: "../assets/icon_reset.png"
                    bgSrc: "../assets/btn_red.png"
                    Layout.preferredWidth: 80; Layout.preferredHeight: 44
                    onClicked: backend.resetHotkey()
                }
            }

            // ════════════════════════════════════
            // 翻譯模式
            // ════════════════════════════════════
            Item { Layout.fillHeight: true }
            SectionLabel { label: backend.tr("翻譯模式", backend.uiLang) }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 10; Layout.rightMargin: 10
                spacing: 12

                ModeCard {
                    text: backend.tr("(A) 覆蓋模式", backend.uiLang)
                    isActive: backend.mode === "overlay"
                    Layout.fillWidth: true; Layout.preferredHeight: 48
                    onClicked: backend.mode = "overlay"
                }
                ModeCard {
                    text: backend.tr("⚓ 錨點模式", backend.uiLang)
                    isActive: backend.mode === "anchor"
                    Layout.fillWidth: true; Layout.preferredHeight: 48
                    onClicked: backend.mode = "anchor"
                }
                ModeCard {
                    text: backend.tr("≡  列表模式", backend.uiLang)
                    isActive: backend.mode === "list"
                    Layout.fillWidth: true; Layout.preferredHeight: 48
                    onClicked: backend.mode = "list"
                }
            }

            // ════════════════════════════════════
            // 模組狀態
            // ════════════════════════════════════
            Item { Layout.fillHeight: true }
            SectionLabel { label: backend.tr("模組狀態", backend.uiLang) }

            BorderImage {
                Layout.fillWidth: true
                Layout.leftMargin: 10; Layout.rightMargin: 10
                Layout.preferredHeight: statusCol.implicitHeight + 20
                Layout.maximumHeight: statusCol.implicitHeight + 20
                source: "../assets/panel_large.png"
                border.left: 20; border.top: 20; border.right: 20; border.bottom: 20

                ColumnLayout {
                    id: statusCol
                    anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                    spacing: 12

                    StatusRow { label: backend.tr("OCR 辨識", backend.uiLang);           moduleState: backend.ocrState }
                    StatusRow { label: backend.transLabel;  moduleState: backend.transState }
                    StatusRow { label: backend.tr("圖像修復", backend.uiLang);           moduleState: backend.inpaintState }
                }
            }

            // ════════════════════════════════════
            // 底部工作狀態列 (利用 Layout.fillHeight 將其推到底部)
            // ════════════════════════════════════
            Item { Layout.fillHeight: true }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 10; Layout.rightMargin: 10
                height: 1
                color: Qt.rgba(0, 0.95, 1, 0.3)
            }

            Text {
                id: globalStatus
                Layout.fillWidth: true
                Layout.bottomMargin: 10
                horizontalAlignment: Text.AlignHCenter
                text: backend.statusText
                color: backend.statusColor
                font { family: "Microsoft JhengHei"; pixelSize: 15; bold: true }

                SequentialAnimation on opacity {
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.6; duration: 1200; easing.type: Easing.InOutSine }
                    NumberAnimation { to: 1.0; duration: 1200; easing.type: Easing.InOutSine }
                }
            }
        }
    }

    // ═══════════════════════════════════════════
    // 可重用元件
    // ═══════════════════════════════════════════

    component SectionLabel: Text {
        property string label
        text: label
        Layout.leftMargin: 10
        Layout.topMargin: 6
        font { family: "Microsoft JhengHei"; pixelSize: 14; bold: true }
        color: cCyan
    }

    component HwCard: BorderImage {
        property string text
        property bool isActive: false
        signal clicked()
        
        source: isActive ? "../assets/btn_gold.png" : "../assets/btn_dark.png"
        border.left: 10; border.top: 10; border.right: 10; border.bottom: 10

        Text {
            anchors.centerIn: parent
            text: parent.text
            font { family: "Microsoft JhengHei"; pixelSize: 14; bold: true }
            color: parent.isActive ? cGold : cSubtext
            Behavior on color { ColorAnimation { duration: 200 } }
        }
        MouseArea {
            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }

    component ModeCard: BorderImage {
        property string text
        property bool isActive: false
        signal clicked()
        
        source: isActive ? "../assets/btn_gold.png" : "../assets/btn_dark.png"
        border.left: 10; border.top: 10; border.right: 10; border.bottom: 10

        Text {
            anchors.centerIn: parent
            text: parent.text
            font { family: "Microsoft JhengHei"; pixelSize: 14; bold: true }
            color: parent.isActive ? cGold : cSubtext
            Behavior on color { ColorAnimation { duration: 200 } }
        }
        MouseArea {
            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
        }
    }

    component NeonButton: BorderImage {
        property string text
        property string iconSrc: ""
        property string bgSrc: "../assets/btn_blue.png"
        signal clicked()
        
        source: bgSrc
        border.left: 10; border.top: 10; border.right: 10; border.bottom: 10

        RowLayout {
            anchors.centerIn: parent
            spacing: 6
            Image {
                visible: parent.parent.iconSrc !== ""
                source: parent.parent.iconSrc
                sourceSize: Qt.size(24, 24)
                Layout.preferredWidth: 24; Layout.preferredHeight: 24
            }
            Text {
                text: parent.parent.text
                font { family: "Microsoft JhengHei"; pixelSize: 13; bold: true }
                color: "#ffffff"
            }
        }
        
        Rectangle {
            id: hoverOverlay
            anchors.fill: parent
            color: "#ffffff"
            opacity: 0
            radius: 8
            Behavior on opacity { NumberAnimation { duration: 150 } }
        }

        MouseArea {
            anchors.fill: parent; cursorShape: Qt.PointingHandCursor
            onClicked: parent.clicked()
            hoverEnabled: true
            onEntered: hoverOverlay.opacity = 0.1
            onExited: hoverOverlay.opacity = 0
            onPressed: hoverOverlay.opacity = 0.2
            onReleased: hoverOverlay.opacity = containsMouse ? 0.1 : 0
        }
    }

    component SettingRow: RowLayout {
        property string label
        property var model: []
        property string currentValue: ""
        signal valueChanged(string v)

        Layout.fillWidth: true
        spacing: 12

        Text {
            text: label
            Layout.preferredWidth: 120
            font { family: "Microsoft JhengHei"; pixelSize: 13 }
            color: cSubtext
            elide: Text.ElideRight
        }

        ComboBox {
            id: combo
            Layout.fillWidth: true
            model: parent.model
            currentIndex: {
                var idx = parent.model.indexOf(parent.currentValue);
                return idx >= 0 ? idx : 0;
            }
            onActivated: parent.valueChanged(currentText)

            background: Rectangle {
                color: "#0a1225"; radius: 6
                border.color: Qt.rgba(0, 0.95, 1, 0.25); border.width: 1
            }
            contentItem: Text {
                text: combo.displayText
                font { family: "Microsoft JhengHei"; pixelSize: 13 }
                color: cCyan
                verticalAlignment: Text.AlignVCenter
                leftPadding: 10
            }
            indicator: Text {
                text: "▾"
                color: cCyan
                font.pixelSize: 14
                anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
            }
            popup: Popup {
                y: combo.height
                width: combo.width
                implicitHeight: contentItem.implicitHeight
                padding: 1
                contentItem: ListView {
                    clip: true
                    implicitHeight: contentHeight
                    model: combo.popup.visible ? combo.delegateModel : null
                    ScrollIndicator.vertical: ScrollIndicator {}
                }
                background: Rectangle { color: "#0a1225"; radius: 6; border.color: cCyan; border.width: 1 }
            }
            delegate: ItemDelegate {
                width: combo.width
                contentItem: Text {
                    text: modelData
                    color: highlighted ? cGold : cText
                    font { family: "Microsoft JhengHei"; pixelSize: 13 }
                    verticalAlignment: Text.AlignVCenter
                }
                highlighted: combo.highlightedIndex === index
                background: Rectangle {
                    color: highlighted ? Qt.rgba(1, 0.84, 0, 0.1) : "transparent"
                }
            }
        }
    }

    component StatusRow: RowLayout {
        property string label
        property string moduleState: "idle"   // idle, loading, ready, error

        Layout.fillWidth: true
        spacing: 8

        // 狀態燈
        Image {
            width: 16; height: 16
            source: moduleState === "ready" ? "../assets/led_green.png" :
                    moduleState === "loading" ? "../assets/led_yellow.png" :
                    moduleState === "error" ? "../assets/led_red.png" : "../assets/led_blue.png"

            // 載入中閃爍
            SequentialAnimation on opacity {
                running: moduleState === "loading"
                loops: Animation.Infinite
                NumberAnimation { to: 0.3; duration: 500 }
                NumberAnimation { to: 1.0; duration: 500 }
            }
        }

        Text {
            text: label
            Layout.fillWidth: true
            font { family: "Microsoft JhengHei"; pixelSize: 13 }
            color: cText
        }

        Text {
            text: moduleState === "ready" ? backend.tr("就緒 ✓", backend.uiLang) :
                  moduleState === "loading" ? backend.tr("載入中...", backend.uiLang) :
                  moduleState === "error" ? backend.tr("失敗 ✗", backend.uiLang) : backend.tr("等待中", backend.uiLang)
            font { family: "Microsoft JhengHei"; pixelSize: 13; bold: true }
            color: moduleState === "ready" ? cGreen :
                   moduleState === "loading" ? cGold :
                   moduleState === "error" ? cRed : cSubtext

            Behavior on color { ColorAnimation { duration: 300 } }
        }
    }
    MouseArea {
        anchors.fill: parent
        z: 9998
        visible: root.isRecordCancelActive
        onClicked: {
            backend.cancelInteractiveRecord()
        }
    }
}
