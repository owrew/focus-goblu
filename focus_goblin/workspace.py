"""Session planning, explainability, companion preferences and data controls."""
import html
import json
import shutil
import statistics
import time
import wave
from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QLineEdit,
    QSpinBox,QComboBox,QCheckBox,QListWidget,QListWidgetItem,QTabWidget,QFileDialog,
    QMessageBox,QTableWidget,QTableWidgetItem,QHeaderView,QProgressBar,QSystemTrayIcon,QMenu)
from .storage import data_dir
from .windows import GlobalPause,SHORTCUTS,set_startup,startup_enabled
from .visuals import GlassPanel


class WorkspaceMixin:
    def setup_features(self):
        self.silenced_until = 0.; self.phone_check = None; self.plan_complete = False
        self.last_explanation = 'No monitoring signals yet.'
        self.hotkey = GlobalPause(self,self.pause)
        self.settings.startup = startup_enabled()
        self.hotkey_status = QLabel(self.hotkey.register(self.settings.global_pause,self.settings.pause_shortcut))
        self.setup_companion_settings()
        self.setup_focus_desk()
        self.setup_history_analytics()
        self.tray=None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray=QSystemTrayIcon(self.windowIcon(),self);self.tray.setToolTip('Focus Goblin · camera status in dashboard')
            menu=QMenu(self)
            for label,callback in [('Open dashboard',lambda:self.pet_action('dashboard')),('Pause / resume',self.pause),('Stop monitoring',self.stop),('Quit',self.close)]:
                action=menu.addAction(label);action.triggered.connect(callback)
            self.tray.setContextMenu(menu);self.tray.activated.connect(lambda reason:self.pet_action('dashboard') if reason==QSystemTrayIcon.ActivationReason.DoubleClick else None);self.tray.show()
        self.explanation = QLabel('Start the camera to see why an alert would trigger.')
        self.explanation.setWordWrap(True); self.explanation.setObjectName('notice')
        self.tabs.widget(0).widget().layout().addWidget(self.explanation,5,0,1,2)
        row = QHBoxLayout()
        self.centralWidget().layout().itemAt(2).layout().addWidget(self.button('False alarm',self.false_alarm))
        row.addWidget(self.button('Make rules gentler',self.gentler))
        row.addWidget(self.button('Check / calibrate phone',self.start_phone_check))
        self.signal_badges.parentWidget().layout().addLayout(row)

    def setup_companion_settings(self):
        index = next(i for i in range(self.tabs.count()) if self.tabs.tabText(i)=='Control room')
        old = self.tabs.widget(index); self.tabs.removeTab(index)
        old.widget().setObjectName('settingsSheet');old.widget().setMaximumWidth(960);old.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        categories = QTabWidget(); categories.addTab(old,'Camera & rules')
        def page(title):
            widget = GlassPanel(); form = QFormLayout(widget);form.setContentsMargins(28,28,28,28);form.setSpacing(14)
            categories.addTab(widget,title); return form
        def line(form,key,label):
            w = QLineEdit(str(getattr(self.settings,key))); self.fields[key] = w; form.addRow(label,w); return w
        def check(form,key,label):
            w = QCheckBox(label); w.setChecked(getattr(self.settings,key)); self.fields[key] = w; form.addRow(w)
        def combo(form,key,label,items):
            w = QComboBox(); w.addItems(items); w.setCurrentText(str(getattr(self.settings,key))); self.fields[key] = w; form.addRow(label,w)
        companion = page('Your goblin')
        line(companion,'goblin_name','Companion name')
        companion.addRow(self.button('Choose goblin body color',self.choose_body_color))
        check(companion,'cursor_follow','Follow the cursor with its eyes')
        check(companion,'poke_reaction','React angrily to a tap (drag still moves the pet)')
        self.sound_path = line(companion,'custom_sound','Custom rage sound (local PCM WAV)')
        companion.addRow(self.button('Import custom WAV',self.import_sound))
        companion.addRow(self.button('Clear custom sound',lambda: self.sound_path.clear()))
        companion.addRow(QLabel('Personalities have different travel, gesture and generated-sound patterns.\nCustom skins are not included, as requested.'))
        companion.addRow(self.button('Apply all settings',self.save_settings,True))
        camera = page('Lighting & phone')
        check(camera,'phone_enabled','Enable visible-phone detection (auto-load bundled model)')
        combo(camera,'phone_backend','Detector',['Balanced YOLOX','Eco YOLOv4','Custom'])
        combo(camera,'phone_size','Eco YOLOv4 input (YOLOX uses 640)',['416','608'])
        check(camera,'auto_light','Automatic face-weighted brightness / local contrast')
        check(camera,'camera_auto_exposure','Ask webcam driver to enable auto exposure on next start')
        w = QSpinBox(); w.setRange(70,180); w.setValue(self.settings.face_brightness); self.fields['face_brightness']=w
        camera.addRow('Target face luminance',w)
        check(camera,'dense_landmarks','Show dense face/iris landmarks in preview')
        camera.addRow(self.button('Run guided phone check',self.start_phone_check))
        camera.addRow(QLabel('Image correction cannot recover clipped highlights or light a dark room.\nSome webcam drivers ignore exposure controls. Restart camera after changing these settings.'))
        camera.addRow(self.button('Apply all settings',self.save_settings,True))
        appearance = page('Scene & system')
        combo(appearance,'background','Background scene',['Waterfall','Aurora'])
        check(appearance,'background_motion','Animate waterfall and ambient light')
        check(appearance,'glass_blur','Blur the scene underneath glass panels')
        check(appearance,'global_pause','Enable a system-wide pause shortcut')
        combo(appearance,'pause_shortcut','Pause / resume shortcut',list(SHORTCUTS))
        appearance.addRow(self.hotkey_status)
        check(appearance,'startup','Start pet at Windows sign-in (camera remains off)')
        retention = QSpinBox(); retention.setRange(0,3650); retention.setValue(self.settings.retention_days); self.fields['retention_days']=retention
        appearance.addRow('Keep history days (0 = keep all)',retention)
        appearance.addRow(QLabel('Retention applies when saved; a recovery backup is created first.\nInstall an update using the newer installer; your local database is preserved.'))
        appearance.addRow(self.button('Apply all settings',self.save_settings,True))
        appearance.addRow(self.button('Install a downloaded update…',self.install_update))
        self.tabs.insertTab(index,categories,'Settings')

    def choose_body_color(self):
        from PySide6.QtWidgets import QColorDialog
        color = QColorDialog.getColor(QColor(self.settings.goblin_color),self)
        if color.isValid(): self.settings.goblin_color=color.name(); self.apply_theme()

    def import_sound(self):
        source,_=QFileDialog.getOpenFileName(self,'Choose a local rage sound','','PCM WAV (*.wav)')
        if not source:return
        try:
            if Path(source).stat().st_size > 20*1024*1024: raise ValueError('Choose a WAV smaller than 20 MB')
            with wave.open(source,'rb') as audio:
                if audio.getcomptype()!='NONE' or audio.getnchannels()>2: raise ValueError('Use mono/stereo PCM WAV')
            folder=data_dir()/'sounds'; folder.mkdir(exist_ok=True)
            target=folder/f'custom-{time.time_ns()}.wav'; shutil.copy2(source,target)
            self.sound_path.setText(str(target))
            self.notice.setText('Sound imported locally. Enable sound and save settings to use it.')
        except (OSError,ValueError,wave.Error) as exc:self.notice.setText(str(exc))

    def setup_focus_desk(self):
        page=GlassPanel(); layout=QVBoxLayout(page);layout.setContentsMargins(24,24,24,24);layout.setSpacing(14)
        title=QLabel('Give your next session a purpose.'); title.setObjectName('brand'); layout.addWidget(title)
        row=QHBoxLayout(); self.session_title=QLineEdit(self.settings.session_name); self.session_title.setPlaceholderText('Session name')
        self.session_length=QSpinBox(); self.session_length.setRange(1,480); self.session_length.setValue(self.settings.session_minutes); self.session_length.setSuffix(' min')
        self.session_title.textChanged.connect(self.persist_plan);self.session_length.valueChanged.connect(self.persist_plan)
        row.addWidget(self.session_title,3); row.addWidget(self.session_length); layout.addLayout(row)
        row=QHBoxLayout(); self.task_entry=QLineEdit(); self.task_entry.setPlaceholderText('Write a task and press Enter to add it and start')
        self.task_entry.returnPressed.connect(self.add_task_and_start); row.addWidget(self.task_entry,3)
        row.addWidget(self.button('Add task',self.add_task)); row.addWidget(self.button('Start planned session',self.start_planned,True)); layout.addLayout(row)
        self.task_list=QListWidget(); self.task_list.itemChanged.connect(self.persist_plan); layout.addWidget(self.task_list,1)
        self.task_list.setStyleSheet('QListWidget {background:rgba(9,24,37,160);border:1px solid #425e72;border-radius:14px;padding:14px;} QListWidget::item {padding:12px;border-bottom:1px solid #294052;}')
        layout.addWidget(self.button('Remove selected task',self.remove_task))
        self.session_clock=QLabel('No planned session running. Pause freezes the countdown.'); self.session_clock.setObjectName('notice'); layout.addWidget(self.session_clock)
        self.session_progress=QProgressBar(); self.session_progress.setRange(0,100); layout.addWidget(self.session_progress)
        self.tabs.insertTab(1,page,'Focus desk')

    def add_task(self):
        text=self.task_entry.text().strip()
        if text:
            item=QListWidgetItem(text[:240]); item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable); item.setCheckState(Qt.CheckState.Unchecked)
            self.task_list.addItem(item); self.task_entry.clear(); self.persist_plan()

    def add_task_and_start(self):self.add_task(); self.start_planned()

    def remove_task(self):
        row=self.task_list.currentRow()
        if row>=0:self.task_list.takeItem(row);self.persist_plan()

    def tasks(self):
        return [{'text':self.task_list.item(i).text(),'done':self.task_list.item(i).checkState()==Qt.CheckState.Checked} for i in range(self.task_list.count())]

    def persist_plan(self,*args):
        if self.sid:
            self.store.save_plan(self.sid,self.session_title.text().strip() or 'Focus session',self.session_length.value()*60,self.tasks())

    def start_planned(self):
        if not self.session_title.text().strip(): self.session_title.setText('Focus session')
        self.settings.session_name=self.session_title.text(); self.settings.session_minutes=self.session_length.value()
        self.store.save_settings(self.settings)
        if self.sid is None:self.start_camera()
        elif self.paused:self.pause()
        if self.sid is None:
            self.notice.setText('Camera is still closing. Wait a moment and start the planned session again.');return
        self.persist_plan(); self.tabs.setCurrentIndex(0)
        self.notice.setText(f'Working on {self.session_title.text()} · {self.session_length.value()} minutes. Tasks are in Focus desk.')

    def plan_started(self):
        self.plan_complete=False;self.persist_plan()

    def update_workspace(self,decision):
        if not hasattr(self,'explanation'):return
        self.last_explanation=f'{decision.reason} · away evidence {self.engine.away:.1f}s / {self.settings.alert_seconds:.1f}s · phone score {self.observation.phone_score:.0%}'
        self.explanation.setText(self.last_explanation)
        if self.phone_check:
            began,scores=self.phone_check
            scores.append(self.observation.phone_score)
            if time.monotonic()-began >= 8:
                useful=[score for score in scores if score>=.15]
                if useful:
                    threshold=max(.15,min(.5,statistics.median(useful)*.65))
                    self.fields['phone_confidence'].setValue(threshold);self.settings.phone_confidence=threshold
                    self.store.save_settings(self.settings)
                    if self.worker:self.worker.settings.phone_confidence=threshold
                    self.notice.setText(f'Phone check found a phone candidate. Threshold set to {threshold:.0%}. This tunes sensitivity; it does not retrain the model.')
                else:self.notice.setText('Phone check found no reliable candidate. Use Balanced YOLOX, move the entire phone into view, improve front lighting, or change its angle. No successful calibration was recorded.')
                self.phone_check=None
        target=self.session_length.value()*60; remaining=max(0,target-self.engine.active)
        done=sum(t['done'] for t in self.tasks()); total=self.task_list.count()
        self.session_clock.setText(f'{self.session_title.text()} · {int(remaining)//60:02d}:{int(remaining)%60:02d} remaining · tasks {done}/{total}')
        self.session_progress.setValue(min(100,round(self.engine.active/target*100)))
        if remaining<=0 and not self.plan_complete:
            self.plan_complete=True;self.persist_plan();self.store.event(self.sid,'goal_complete','Planned session duration reached')
            self.pause();self.notice.setText('Session time complete. Review your tasks or take a break. Monitoring is paused.')

    def false_alarm(self):
        if not self.sid:self.notice.setText('Start a session before marking a false alarm.');return
        self.store.event(self.sid,'false_alarm',self.last_explanation)
        self.engine.dismiss_alert();self.silenced_until=time.monotonic()+30;self.preview_until=0;self.screen_fire.clear()
        if hasattr(self,'sound_effect'):self.sound_effect.stop()
        self.notice.setText('Marked as a false alarm. Reactions silenced for 30 seconds; measured analytics continue. Tune tolerances or use Make rules gentler.')

    def gentler(self):
        for key in ('head_tolerance','gaze_tolerance'):
            value=min(.8,getattr(self.settings,key)*1.15);setattr(self.settings,key,value);self.fields[key].setValue(value)
        self.engine.settings=self.settings;self.store.save_settings(self.settings)
        self.notice.setText('Head and gaze tolerances increased by 15%. Other rules are unchanged.')

    def start_phone_check(self):
        if self.demo and self.sid:self.notice.setText('Stop demo first to check a real phone.');return
        self.settings.phone_enabled=True;self.fields['phone_enabled'].setChecked(True)
        self.settings.phone_confidence=.25;self.fields['phone_confidence'].setValue(.25)
        if not self.sid:self.start_camera()
        elif self.paused:self.pause()
        elif self.worker and not self.worker.settings.phone_enabled:
            self.notice.setText('Phone detection was off. Stop and start the camera, then run Phone check.');return
        if self.sid is None:
            self.notice.setText('Camera is still closing. Wait a moment and run Phone Check again.');return
        self.phone_check=(time.monotonic(),[])
        self.notice.setText('Phone check: hold the whole phone in view for 8 seconds; try both front and back. Watch the phone box and score. No frames are saved.')

    def setup_history_analytics(self):
        from .ui import Chart
        index=next(i for i in range(self.tabs.count()) if self.tabs.tabText(i)=='Session archive')
        layout=self.tabs.widget(index).layout()
        self.history_range=QComboBox();self.history_range.addItems(['Weekly · 7 days','Monthly · 30 days','Quarter · 90 days'])
        self.history_range.currentIndexChanged.connect(self.refresh_analytics);layout.insertWidget(1,self.history_range)
        self.analytics_chart=Chart(True);layout.insertWidget(2,self.analytics_chart)
        self.analytics_summary=QLabel();layout.insertWidget(3,self.analytics_summary)
        layout.insertWidget(4,self.button("Generate comparison report",self.export_comparison))
        self.event_table=QTableWidget(0,3);self.event_table.setHorizontalHeaderLabels(['When','Event','Explanation'])
        self.event_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.event_table)
        self.history.itemSelectionChanged.connect(self.show_session_events)
        self.event_table.itemDoubleClicked.connect(self.open_session_event)
        row=QHBoxLayout()
        row.addWidget(self.button('Export all data JSON',self.export_json));row.addWidget(self.button('Back up database',self.backup_data))
        row.addWidget(self.button('Delete selected sessions',self.delete_selected));row.addWidget(self.button('Open data folder',lambda:QDesktopServices.openUrl(QUrl.fromLocalFile(str(data_dir())))))
        layout.addLayout(row);self.refresh_analytics()

    def refresh_analytics(self,*args):
        days = [7,30,90][self.history_range.currentIndex()]
        self.analytics_chart.values = self.store.daily_range(days)
        self.analytics_chart.update()
        current, previous = self.store.comparison(days)
        delta = (current['focus']-previous['focus'])/60
        self.analytics_summary.setText(
            f"{current['focus']/60:.1f} focus min | {delta:+.1f} min vs previous {days} days | "
            f"{current['distracted']/60:.1f} distraction min | {current['sessions']} sessions")

    def export_comparison(self):
        days = [7,30,90][self.history_range.currentIndex()]
        path,_ = QFileDialog.getSaveFileName(self,'Save focus comparison',f'focus-{days}-day-report.html','HTML (*.html)')
        if not path:
            return
        current, previous = self.store.comparison(days)
        rows = []
        for label,key,div in [('Estimated focus (min)','focus',60),('Likely distraction (min)','distracted',60),
                              ('Unknown and grace (min)','unknown',60),('Absent (min)','absent',60),
                              ('Alerts','alerts',1),('Sessions','sessions',1)]:
            a,b = current[key]/div,previous[key]/div
            rows.append(f'<tr><th>{html.escape(label)}</th><td>{a:g}</td><td>{b:g}</td><td>{a-b:+g}</td></tr>')
        daily = ''.join(f'<li>{day}: {seconds/60:.1f} min</li>' for day,seconds in self.store.daily_range(days))
        report = ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Focus Goblin report</title>'
                  '<style>body{background:#101a26;color:#eaf2f5;font:16px system-ui;max-width:760px;margin:3rem auto;padding:0 1rem}'
                  'table{width:100%;border-collapse:collapse}th,td{padding:.7rem;text-align:left;border-bottom:1px solid #385064}'
                  'h1,h2{color:#86dfc9}li{margin:.25rem 0}</style>'
                  f'<h1>Focus Goblin | {days}-day comparison</h1>'
                  f"<p>{current['range']} compared with {previous['range']}.</p>"
                  '<p>Local session estimates grouped by start date. Demo sessions excluded. The current period includes today.</p>'
                  '<table><thead><tr><th>Measure</th><th>Current</th><th>Previous</th><th>Change</th></tr></thead>'
                  f"<tbody>{''.join(rows)}</tbody></table><h2>Daily estimated focus</h2><ul>{daily}</ul></html>")
        try:
            Path(path).write_text(report,encoding='utf-8')
            self.notice.setText('Comparison report saved. Open the HTML file in your browser to view or print it.')
        except OSError as exc:
            self.notice.setText(f'Could not save report: {exc}')

    def show_session_events(self):
        row=self.history.currentRow()
        if row<0 or row>=len(getattr(self,'history_ids',[])):return
        sid=self.history_ids[row];events=self.store.events_for(sid);self.event_table.setRowCount(len(events))
        for i,event in enumerate(events):
            for j,value in enumerate(event):self.event_table.setItem(i,j,QTableWidgetItem(str(value)))

    def open_session_event(self, item):
        detail = self.event_table.item(item.row(),2)
        if detail:
            dialog = QMessageBox(self)
            dialog.setWindowTitle('Session event')
            dialog.setTextFormat(Qt.TextFormat.PlainText)
            dialog.setText(detail.text())
            dialog.exec()

    def export_json(self):
        path,_=QFileDialog.getSaveFileName(self,'Export all analytics','focus-data.json','JSON (*.json)')
        if path:self.store.export_all(path)

    def backup_data(self):
        path,_=QFileDialog.getSaveFileName(self,'Back up local history','focus-backup.sqlite3','SQLite (*.sqlite3)')
        if path:self.store.backup(path)

    def delete_selected(self):
        ids=[self.history_ids[index.row()] for index in self.history.selectionModel().selectedRows()]
        ids=[sid for sid in ids if sid!=self.sid]
        if not ids:return
        if QMessageBox.question(self,'Delete selected history?',f'Delete {len(ids)} selected sessions? A local recovery backup will be saved first.')!=QMessageBox.StandardButton.Yes:return
        self.store.backup(data_dir()/f'before-delete-{time.time_ns()}.sqlite3');self.store.delete_sessions(ids);self.refresh_history()

    def install_update(self):
        source,_=QFileDialog.getOpenFileName(self,'Choose a trusted downloaded Focus Goblin installer','','Installer (*.exe)')
        if not source:return
        if QMessageBox.question(self,'Run update installer?',f'Run this installer?\n{source}\nYour session will stop and the app will close. Only use installers you trust.')!=QMessageBox.StandardButton.Yes:return
        import subprocess
        self.stop()
        try:subprocess.Popen([source],close_fds=True)
        except OSError as exc:self.notice.setText(str(exc));return
        self.close()
