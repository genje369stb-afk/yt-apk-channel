import flet as ft
import requests
import calendar
import json
import os
from datetime import datetime

# =====================================================================
# URL DATABASE BAWAAN (DEFAULT)
# Jika nanti pindah PC / buat database baru, cukup klik tombol ⚙️ DB
# di pojok kanan atas aplikasi HP tanpa perlu build ulang APK!
# =====================================================================
DEFAULT_FIREBASE_URL = "https://yt-channel-manager-317da-default-rtdb.asia-southeast1.firebasedatabase.app"

# Batas maksimal siklus upload (7 hari).
# Notifikasi akan berbunyi mulai 3 hari sebelum batas 7 hari berakhir (hari ke-4, 5, 6, dst.)
BATAS_DEADLINE_HARI = 7


# =====================================================================
# FUNGSI KOMPATIBILITAS OTOMATIS (JALAN DI FLET PC TERBARU & FLET APK)
# =====================================================================
def make_border_all(width, color):
    if hasattr(ft, "Border") and hasattr(ft.Border, "all"):
        return ft.Border.all(width, color)
    return ft.border.all(width, color)


def make_padding_only(left=0, top=0, right=0, bottom=0):
    if hasattr(ft, "Padding") and hasattr(ft.Padding, "only"):
        return ft.Padding.only(left=left, top=top, right=right, bottom=bottom)
    return ft.padding.only(left=left, top=top, right=right, bottom=bottom)


def make_button(text, bgcolor, color="#ffffff", on_click=None, width=None, height=None, expand=False):
    if hasattr(ft, "ElevatedButton"):
        return ft.ElevatedButton(
            text=text,
            bgcolor=bgcolor,
            color=color,
            width=width,
            height=height,
            expand=expand,
            on_click=on_click,
        )
    else:
        return ft.Button(
            content=ft.Text(text, color=color, weight=ft.FontWeight.BOLD, size=12),
            bgcolor=bgcolor,
            width=width,
            height=height,
            expand=expand,
            on_click=on_click,
        )


def make_outlined_button(text, color="#38bdf8", on_click=None, expand=False):
    try:
        return ft.OutlinedButton(
            content=ft.Text(text, color=color, weight=ft.FontWeight.BOLD, size=12),
            expand=expand,
            on_click=on_click,
        )
    except Exception:
        return ft.OutlinedButton(
            text=text,
            expand=expand,
            on_click=on_click,
        )


def open_dialog_compat(page, dlg):
    try:
        if hasattr(page, "show_dialog"):
            page.show_dialog(dlg)
            return
    except Exception:
        pass
    if dlg not in page.overlay:
        page.overlay.append(dlg)
    dlg.open = True
    page.update()


def close_dialog_compat(page, dlg):
    try:
        if hasattr(page, "pop_dialog"):
            page.pop_dialog()
            return
    except Exception:
        pass
    dlg.open = False
    page.update()


def main(page: ft.Page):
    page.title = "YT Manager Mobile"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#09090b"
    page.padding = 0

    try:
        page.window.width = 410
        page.window.height = 800
    except Exception:
        pass

    channels_data = {}
    notifikasi_sudah_muncul_sesi_ini = {"shown": False}

    # ==========================================
    # PENYIMPANAN LINK DATABASE PERMANEN DI HP & PC
    # ==========================================
    def get_saved_db_url():
        try:
            if hasattr(page, "client_storage"):
                saved = page.client_storage.get("custom_firebase_url")
                if saved and saved.strip():
                    return saved.strip()
        except Exception:
            pass

        base_dir = os.path.dirname(os.path.abspath(__file__))
        for path in [os.path.join(base_dir, "db_config.json"), os.path.join(base_dir, "..", "db_config.json")]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        url = json.load(f).get("firebase_url", "").strip()
                        if url:
                            return url
                except Exception:
                    pass

        return DEFAULT_FIREBASE_URL.strip()

    def save_custom_db_url(new_url):
        clean = new_url.strip().rstrip("/")
        if clean.endswith(".json"):
            clean = clean[:-5].rstrip("/")
        if clean.endswith("/channels"):
            clean = clean[:-9].rstrip("/")

        try:
            if hasattr(page, "client_storage"):
                page.client_storage.set("custom_firebase_url", clean)
        except Exception:
            pass

        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            cfg_path = os.path.join(base_dir, "db_config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump({"firebase_url": clean}, f, indent=2)
        except Exception:
            pass

        return clean

    def show_snack(pesan, warna="#16a34a"):
        snack = ft.SnackBar(
            content=ft.Text(pesan, color="#ffffff", weight=ft.FontWeight.BOLD),
            bgcolor=warna,
        )
        open_dialog_compat(page, snack)

    def get_endpoint():
        url = get_saved_db_url()
        if not url:
            return None
        clean = url.rstrip("/")
        if clean.endswith(".json"):
            clean = clean[:-5].rstrip("/")
        if clean.endswith("/channels"):
            clean = clean[:-9].rstrip("/")
        return f"{clean}/channels"

    # ==========================================
    # LOGIKA PENGECEKAN NOTIFIKASI (H-3 SEBELUM DEADLINE)
    # ==========================================
    def kumpulkan_channel_wajib_upload():
        daftar_notif = []
        hari_ini = datetime.now().date()
        sorted_items = sorted(channels_data.items(), key=parse_sort_key)

        for ch_id, item in sorted_items:
            nama = item.get("nama_channel", "Tanpa Nama")
            tgl_str = item.get("last_upload", "").strip()
            try:
                tgl_upload = datetime.strptime(tgl_str, "%Y-%m-%d").date()
                selisih = (hari_ini - tgl_upload).days
                sisa_ke_deadline = BATAS_DEADLINE_HARI - selisih

                # Kondisi 1: 3 hari sebelum batas 7 hari berakhir (hari ke-4 s/d ke-7)
                if 4 <= selisih <= 7:
                    if sisa_ke_deadline == 0:
                        ket_waktu = "Deadline Hari Ini! (Sudah 7 hari belum upload)"
                    else:
                        ket_waktu = f"Sisa {sisa_ke_deadline} hari sebelum deadline ({selisih} hari lalu)"
                    daftar_notif.append({
                        "nama": nama,
                        "pesan": f"Segera lakukan upload di channel {nama}",
                        "detail": ket_waktu,
                        "warna": "#d97706"
                    })

                # Kondisi 2: Sudah lewat batas deadline (> 7 hari / Pasif)
                elif selisih > 7:
                    daftar_notif.append({
                        "nama": nama,
                        "pesan": f"Segera lakukan upload di channel {nama}",
                        "detail": f"Sudah lewat deadline! ({selisih} hari belum upload)",
                        "warna": "#dc2626"
                    })

                # Kondisi 3: Jika user mengatur tanggal di masa depan (H-3 sampai H-1 jadwal upload)
                elif -3 <= selisih < 0:
                    daftar_notif.append({
                        "nama": nama,
                        "pesan": f"Segera lakukan upload di channel {nama}",
                        "detail": f"Jadwal upload {abs(selisih)} hari lagi ({tgl_str})",
                        "warna": "#0284c7"
                    })
            except Exception:
                pass

        return daftar_notif

    def open_notification_dialog(auto_trigger=False):
        daftar_notif = kumpulkan_channel_wajib_upload()

        if auto_trigger and len(daftar_notif) == 0:
            return

        def tutup_notif(e=None):
            close_dialog_compat(page, dlg_notif)

        list_notif_controls = []
        if len(daftar_notif) == 0:
            list_notif_controls.append(
                ft.Container(
                    padding=16,
                    bgcolor="#27272a",
                    border_radius=8,
                    content=ft.Text(
                        "✅ Semua channel masih dalam batas aman!\nBelum ada channel yang mendekati 3 hari sebelum deadline.",
                        size=12,
                        color="#4ade80",
                        text_align=ft.TextAlign.CENTER,
                    ),
                )
            )
        else:
            for item_n in daftar_notif:
                list_notif_controls.append(
                    ft.Container(
                        bgcolor="#27272a",
                        border=make_border_all(1, item_n["warna"]),
                        border_radius=8,
                        padding=10,
                        content=ft.Column([
                            ft.Text(
                                f"⚠️ {item_n['pesan']}",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color="#ffffff",
                            ),
                            ft.Text(
                                f"⏰ {item_n['detail']}",
                                size=11,
                                color=item_n["warna"],
                                weight=ft.FontWeight.BOLD,
                            ),
                        ], spacing=3),
                    )
                )

        dlg_notif = ft.AlertDialog(
            bgcolor="#18181b",
            title=ft.Row([
                ft.Text(
                    f"🔔 Peringatan Upload ({len(daftar_notif)})",
                    size=15,
                    weight=ft.FontWeight.BOLD,
                    color="#facc15" if daftar_notif else "#4ade80",
                )
            ]),
            content=ft.Container(
                width=310,
                height=280 if len(daftar_notif) > 2 else None,
                content=ft.Column(
                    controls=list_notif_controls,
                    spacing=8,
                    scroll=ft.ScrollMode.AUTO,
                    tight=True,
                ),
            ),
            actions=[
                make_button("Mengerti & Tutup", bgcolor="#2563eb", on_click=tutup_notif),
            ],
        )

        open_dialog_compat(page, dlg_notif)

    # ==========================================
    # POPUP GANTI DATABASE (UNTUK PINDAH PC / DB BARU)
    # ==========================================
    def open_db_settings_dialog(e=None):
        current_url = get_saved_db_url()
        txt_url_input = ft.TextField(
            value=current_url,
            label="Link Firebase Database",
            hint_text="https://nama-project-default-rtdb.firebasedatabase.app",
            text_size=12,
            border_color="#38bdf8",
            bgcolor="#27272a",
            color="#ffffff",
        )

        def tutup_dlg(e=None):
            close_dialog_compat(page, dlg_db)

        def simpan_db_baru(e):
            val = (txt_url_input.value or "").strip()
            if not val.startswith("https://"):
                show_snack("⚠️ Link harus diawali https://", "#d97706")
                return
            save_custom_db_url(val)
            tutup_dlg()
            show_snack("✅ Database baru berhasil disimpan!", "#16a34a")
            notifikasi_sudah_muncul_sesi_ini["shown"] = False
            sync_data()

        def reset_ke_default(e):
            save_custom_db_url(DEFAULT_FIREBASE_URL)
            tutup_dlg()
            show_snack("🔄 Dikembalikan ke Database Bawaan", "#0284c7")
            notifikasi_sudah_muncul_sesi_ini["shown"] = False
            sync_data()

        dlg_db = ft.AlertDialog(
            bgcolor="#18181b",
            title=ft.Text("⚙️ Pengaturan Link Database", size=16, weight=ft.FontWeight.BOLD, color="#f4f4f5"),
            content=ft.Container(
                width=300,
                content=ft.Column([
                    ft.Text(
                        "Jika Anda membuat database baru di PC lain, salin Link Database dari aplikasi PC lalu tempelkan di bawah ini:",
                        size=12, color="#a1a1aa"
                    ),
                    txt_url_input,
                ], tight=True, spacing=10)
            ),
            actions=[
                ft.TextButton("Reset Bawaan", on_click=reset_ke_default),
                ft.TextButton("Batal", on_click=tutup_dlg),
                make_button("Simpan", bgcolor="#16a34a", on_click=simpan_db_baru),
            ]
        )

        open_dialog_compat(page, dlg_db)

    # ==========================================
    # LOGIKA SORTING & SELISIH HARI
    # ==========================================
    def parse_sort_key(item_tuple):
        _, data = item_tuple
        tgl_str = data.get("last_upload", "").strip()
        nama_str = data.get("nama_channel", "").lower()
        try:
            tgl_obj = datetime.strptime(tgl_str, "%Y-%m-%d").date()
        except Exception:
            tgl_obj = datetime.min.date()
        return (tgl_obj, nama_str)

    def hitung_selisih_hari(tanggal_str):
        try:
            tgl_upload = datetime.strptime(tanggal_str.strip(), "%Y-%m-%d").date()
            hari_ini = datetime.now().date()
            selisih = (hari_ini - tgl_upload).days
            sisa = BATAS_DEADLINE_HARI - selisih
            if selisih == 0:
                return "Upload Hari Ini (Aman)", "#16a34a"
            elif selisih < 0:
                return f"Terjadwal ({abs(selisih)} hari lagi)", "#0284c7"
            elif selisih <= 3:
                return f"{selisih} hari lalu • Sisa {sisa} hr (Aman)", "#16a34a"
            elif selisih <= 7:
                return f"⚠️ H-{sisa} Deadline! ({selisih} hr lalu)", "#d97706"
            else:
                return f"🚨 Lewat Deadline! ({selisih} hr lalu)", "#dc2626"
        except Exception:
            return "Format Bebas", "#52525b"

    def update_tanggal_channel(ch_id, nama_ch, tanggal_baru):
        endpoint = get_endpoint()
        if not endpoint:
            show_snack("⚠️ Link Database belum diatur!", "#d97706")
            return

        try:
            res = requests.patch(
                f"{endpoint}/{ch_id}.json",
                json={"last_upload": tanggal_baru},
                timeout=10
            )
            if res.status_code == 200:
                show_snack(f"✅ {nama_ch} diupdate ke {tanggal_baru}", "#16a34a")
                sync_data()
            else:
                show_snack(f"❌ Gagal update: HTTP {res.status_code}", "#dc2626")
        except Exception as e:
            show_snack(f"❌ Error koneksi: {e}", "#dc2626")

    # ==========================================
    # DIALOG POPUP KALENDER INTERAKTIF
    # ==========================================
    def open_calendar_dialog(ch_id, nama_ch, current_date_str):
        try:
            dt = datetime.strptime(current_date_str.strip(), "%Y-%m-%d")
            state = {"year": dt.year, "month": dt.month, "selected": dt.date()}
        except Exception:
            now = datetime.now()
            state = {"year": now.year, "month": now.month, "selected": now.date()}

        nama_bulan = [
            "", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]

        lbl_ym = ft.Text("", size=15, weight=ft.FontWeight.BOLD, color="#f4f4f5")
        cal_grid = ft.Column(spacing=4)

        def tutup_dialog(e=None):
            close_dialog_compat(page, dlg_cal)

        def pilih_dan_tutup(tgl_str):
            tutup_dialog()
            update_tanggal_channel(ch_id, nama_ch, tgl_str)

        def render_cal():
            cal_grid.controls.clear()
            lbl_ym.value = f"{nama_bulan[state['month']]} {state['year']}"

            hari_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            for idx_h, h in enumerate(["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]):
                hari_row.controls.append(
                    ft.Container(
                        content=ft.Text(
                            h, size=11, weight=ft.FontWeight.BOLD,
                            color="#ef4444" if idx_h == 6 else "#a1a1aa"
                        ),
                        width=36
                    )
                )
            cal_grid.controls.append(hari_row)

            cal_matrix = calendar.monthcalendar(state["year"], state["month"])
            today = datetime.now().date()

            for week in cal_matrix:
                w_row = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                for day in week:
                    if day == 0:
                        w_row.controls.append(ft.Container(width=36, height=34))
                    else:
                        curr_d = datetime(state["year"], state["month"], day).date()
                        if curr_d == state["selected"]:
                            bg = "#dc2626"
                        elif curr_d == today:
                            bg = "#0284c7"
                        else:
                            bg = "#27272a"

                        tgl_formatted = f"{state['year']:04d}-{state['month']:02d}-{day:02d}"
                        w_row.controls.append(
                            ft.Container(
                                content=ft.Text(str(day), size=12, color="#ffffff", weight=ft.FontWeight.BOLD),
                                width=36,
                                height=34,
                                bgcolor=bg,
                                border_radius=6,
                                padding=8,
                                on_click=lambda e, t=tgl_formatted: pilih_dan_tutup(t)
                            )
                        )
                cal_grid.controls.append(w_row)
            page.update()

        def prev_m(e):
            if state["month"] == 1:
                state["month"] = 12
                state["year"] -= 1
            else:
                state["month"] -= 1
            render_cal()

        def next_m(e):
            if state["month"] == 12:
                state["month"] = 1
                state["year"] += 1
            else:
                state["month"] += 1
            render_cal()

        today_str = datetime.now().strftime("%Y-%m-%d")

        dlg_cal = ft.AlertDialog(
            bgcolor="#18181b",
            title=ft.Column([
                ft.Text("📅 Edit Tanggal Upload", size=16, weight=ft.FontWeight.BOLD, color="#f4f4f5"),
                ft.Text(nama_ch, size=12, color="#38bdf8"),
            ], spacing=2),
            content=ft.Container(
                width=290,
                content=ft.Column([
                    ft.Container(
                        bgcolor="#27272a",
                        border_radius=8,
                        padding=4,
                        content=ft.Row([
                            ft.TextButton("◀", on_click=prev_m),
                            lbl_ym,
                            ft.TextButton("▶", on_click=next_m),
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    ),
                    cal_grid,
                    ft.Divider(color="#27272a", height=12),
                    make_button(
                        text=f"⚡ Pilih Hari Ini ({today_str})",
                        bgcolor="#2563eb",
                        width=290,
                        height=40,
                        on_click=lambda e: pilih_dan_tutup(today_str)
                    )
                ], tight=True, spacing=8)
            ),
            actions=[
                ft.TextButton("Batal", on_click=tutup_dialog)
            ]
        )

        render_cal()
        open_dialog_compat(page, dlg_cal)

    # ==========================================
    # KOMPONEN DAFTAR CARD, HEADER & FOOTER
    # ==========================================
    lbl_status_sync = ft.Text("Status: Menunggu sinkronisasi...", size=11, color="#a1a1aa")
    lbl_total_channel = ft.Text(
        "Daftar Channel (0) • Urut Prioritas",
        size=14, weight=ft.FontWeight.BOLD, color="#f4f4f5"
    )

    list_cards = ft.ListView(expand=True, spacing=10, padding=14)

    def render_cards():
        list_cards.controls.clear()
        total = len(channels_data)
        lbl_total_channel.value = f"Daftar Channel ({total}) • Urut Prioritas"

        if total == 0:
            list_cards.controls.append(
                ft.Container(
                    padding=40,
                    content=ft.Text(
                        "Belum ada data channel di database ini.\nJika Anda baru mengganti database di PC lain, tekan tombol ⚙️ DB di pojok kanan atas untuk mengganti Link Database.",
                        color="#71717a",
                        text_align=ft.TextAlign.CENTER,
                        size=13
                    )
                )
            )
            page.update()
            return

        sorted_items = sorted(channels_data.items(), key=parse_sort_key)
        today_str = datetime.now().strftime("%Y-%m-%d")

        for idx, (ch_id, item) in enumerate(sorted_items):
            nama = item.get("nama_channel", "Tanpa Nama")
            email = item.get("email", "-")
            last_up = item.get("last_upload", "-")
            ket = item.get("keterangan", "-")

            info_hari, badge_color = hitung_selisih_hari(last_up)

            perlu_peringatan = badge_color in ("#d97706", "#dc2626")
            komponen_peringatan = []
            if perlu_peringatan:
                komponen_peringatan.append(
                    ft.Container(
                        bgcolor="#27272a",
                        border=make_border_all(1, badge_color),
                        border_radius=6,
                        padding=6,
                        content=ft.Text(
                            f"🔔 Segera lakukan upload di channel {nama}!",
                            size=11,
                            weight=ft.FontWeight.BOLD,
                            color="#facc15" if badge_color == "#d97706" else "#fca5a5",
                        ),
                    )
                )

            card = ft.Container(
                bgcolor="#18181b",
                border=make_border_all(2, badge_color),
                border_radius=12,
                padding=12,
                content=ft.Column([
                    ft.Row([
                        ft.Text(
                            f"#{idx + 1}  📺 {nama}",
                            size=15, weight=ft.FontWeight.BOLD, color=badge_color, expand=True
                        ),
                        ft.Container(
                            bgcolor=badge_color,
                            border_radius=6,
                            padding=6,
                            content=ft.Text(f"📅 {last_up}", size=11, weight=ft.FontWeight.BOLD, color="#ffffff")
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

                    ft.Text(f"Status: {info_hari}", size=12, weight=ft.FontWeight.BOLD, color=badge_color),
                    *komponen_peringatan,
                    ft.Text(f"✉️ {email}", size=12, color="#a1a1aa"),
                    ft.Text(f"📝 {ket if ket else 'Tidak ada catatan'}", size=12, color="#71717a"),

                    ft.Divider(color="#27272a", height=8),

                    ft.Row([
                        make_outlined_button(
                            text="📅 Pilih Kalender",
                            expand=True,
                            on_click=lambda e, cid=ch_id, nm=nama, lu=last_up: open_calendar_dialog(cid, nm, lu)
                        ),
                        make_button(
                            text="⚡ Set Hari Ini",
                            bgcolor="#16a34a",
                            expand=True,
                            on_click=lambda e, cid=ch_id, nm=nama: update_tanggal_channel(cid, nm, today_str)
                        )
                    ], spacing=8)
                ], spacing=4)
            )
            list_cards.controls.append(card)

        page.update()

    def sync_data(e=None):
        endpoint = get_endpoint()
        if not endpoint:
            lbl_status_sync.value = "⚠️ Klik tombol ⚙️ DB di atas untuk mengatur Link Database"
            lbl_status_sync.color = "#facc15"
            page.update()
            return

        lbl_status_sync.value = "⏳ Menyinkronkan data dari Cloud..."
        lbl_status_sync.color = "#38bdf8"
        page.update()

        try:
            res = requests.get(f"{endpoint}.json", timeout=10)
            if res.status_code == 200:
                data = res.json()
                channels_data.clear()
                if isinstance(data, dict):
                    channels_data.update(data)
                waktu = datetime.now().strftime("%H:%M:%S")
                lbl_status_sync.value = f"✅ Terhubung & Disinkronkan ({waktu})"
                lbl_status_sync.color = "#4ade80"
                render_cards()

                if not notifikasi_sudah_muncul_sesi_ini["shown"]:
                    notifikasi_sudah_muncul_sesi_ini["shown"] = True
                    open_notification_dialog(auto_trigger=True)
            else:
                lbl_status_sync.value = f"❌ Gagal sinkron (HTTP {res.status_code})"
                lbl_status_sync.color = "#f87171"
                page.update()
        except Exception as err:
            lbl_status_sync.value = "❌ Gagal sinkron: Periksa koneksi / Link DB"
            lbl_status_sync.color = "#f87171"
            show_snack(f"Error: {err}", "#dc2626")
            page.update()

    # ==========================================
    # HEADER DENGAN JARAK AMAN DARI STATUS BAR HP
    # ==========================================
    header_bar = ft.Container(
        bgcolor="#18181b",
        # Diberi jarak atas (top=36) agar turun ke bawah dan tidak tertutup jam/baterai HP
        padding=make_padding_only(left=14, top=36, right=14, bottom=12),
        content=ft.Column([
            # Baris Judul + Tombol 🔔 Notif + Tombol ⚙️ DB + Tombol 🔄 Sinkron
            ft.Row([
                ft.Text("▶ YT MANAGER", size=15, weight=ft.FontWeight.BOLD, color="#ef4444"),
                ft.Row([
                    make_button(
                        text="🔔",
                        bgcolor="#d97706",
                        color="#ffffff",
                        height=36,
                        on_click=lambda e: open_notification_dialog(auto_trigger=False)
                    ),
                    make_button(
                        text="⚙️ DB",
                        bgcolor="#27272a",
                        color="#38bdf8",
                        height=36,
                        on_click=open_db_settings_dialog
                    ),
                    make_button(
                        text="🔄 Sinkron",
                        bgcolor="#2563eb",
                        color="#ffffff",
                        height=36,
                        on_click=sync_data
                    ),
                ], spacing=6)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            ft.Row([lbl_total_channel, lbl_status_sync], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),

            ft.Container(
                bgcolor="#09090b",
                border=make_border_all(1, "#27272a"),
                border_radius=8,
                padding=8,
                content=ft.Column([
                    ft.Text(
                        "Keterangan Warna (Urut Prioritas Terlama ➔ Terbaru):",
                        size=10, weight=ft.FontWeight.BOLD, color="#d4d4d8"
                    ),
                    ft.Row([
                        ft.Column([
                            ft.Row([
                                ft.Container(width=10, height=10, bgcolor="#dc2626", border_radius=3),
                                ft.Text("Merah: Pasif (> 7 Hr)", size=10, color="#e4e4e7")
                            ], spacing=5),
                            ft.Row([
                                ft.Container(width=10, height=10, bgcolor="#d97706", border_radius=3),
                                ft.Text("Oranye: H-3 Deadline (4–7 Hr)", size=10, color="#e4e4e7")
                            ], spacing=5),
                        ], spacing=3, expand=True),
                        ft.Column([
                            ft.Row([
                                ft.Container(width=10, height=10, bgcolor="#16a34a", border_radius=3),
                                ft.Text("Hijau: Aman (0–3 Hr)", size=10, color="#e4e4e7")
                            ], spacing=5),
                            ft.Row([
                                ft.Container(width=10, height=10, bgcolor="#0284c7", border_radius=3),
                                ft.Text("Biru: Terjadwal", size=10, color="#e4e4e7")
                            ], spacing=5),
                        ], spacing=3, expand=True),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=4)
            )
        ], spacing=6)
    )

    # ==========================================
    # FOOTER MERAH PERMANEN DI BAGIAN BAWAH
    # ==========================================
    footer_bar = ft.Container(
        bgcolor="#dc2626",
        padding=make_padding_only(left=10, top=10, right=10, bottom=12),
        content=ft.Row(
            [
                ft.Text(
                    "Untuk Menambah Channel Silahkan Buka Versi Dekstop/PC",
                    size=12,
                    weight=ft.FontWeight.BOLD,
                    color="#ffffff",
                    text_align=ft.TextAlign.CENTER,
                )
            ],
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    )

    main_layout = ft.Column([header_bar, list_cards, footer_bar], expand=True, spacing=0)

    # Bungkus dengan SafeArea agar tidak menabrak status bar atas & navigasi bawah Android
    if hasattr(ft, "SafeArea"):
        page.add(ft.SafeArea(content=main_layout, expand=True))
    else:
        page.add(main_layout)

    sync_data()


if __name__ == "__main__":
    if hasattr(ft, "app"):
        ft.app(target=main)
    else:
        ft.run(main)
