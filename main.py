import flet as ft
import requests
import calendar
import json
import os
from datetime import datetime

# =====================================================================
# PASTIKAN LINK DATABASE FIREBASE KAMU TERTULIS DI BAWAH INI:
# =====================================================================
DEFAULT_FIREBASE_URL = "https://yt-channel-manager-317da-default-rtdb.asia-southeast1.firebasedatabase.app"


def load_database_url():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(base_dir, "db_config.json"),
        os.path.join(base_dir, "..", "db_config.json"),
    ]
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    url = json.load(f).get("firebase_url", "").strip()
                    if url:
                        return url
            except Exception:
                pass
    return DEFAULT_FIREBASE_URL.strip()


def main(page: ft.Page):
    page.title = "YT Manager Mobile"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#09090b"
    page.padding = 0

    channels_data = {}

    def show_snack(pesan, warna="#16a34a"):
        snack = ft.SnackBar(
            content=ft.Text(pesan, color="#ffffff", weight=ft.FontWeight.BOLD),
            bgcolor=warna,
        )
        try:
            page.overlay.append(snack)
            snack.open = True
            page.update()
        except Exception:
            pass

    def get_endpoint():
        url = load_database_url()
        if not url:
            return None
        clean = url.rstrip("/")
        if clean.endswith(".json"):
            clean = clean[:-5].rstrip("/")
        if clean.endswith("/channels"):
            clean = clean[:-9].rstrip("/")
        return f"{clean}/channels"

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
            if selisih == 0:
                return "Upload Hari Ini", "#16a34a"
            elif selisih < 0:
                return f"Terjadwal ({abs(selisih)} hari lagi)", "#0284c7"
            elif selisih <= 3:
                return f"{selisih} hari lalu (Aman)", "#16a34a"
            elif selisih <= 7:
                return f"{selisih} hari lalu (Perlu Upload)", "#d97706"
            else:
                return f"{selisih} hari lalu (Pasif!)", "#dc2626"
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
            dlg_cal.open = False
            page.update()

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
                    ft.ElevatedButton(
                        text=f"⚡ Pilih Hari Ini ({today_str})",
                        bgcolor="#2563eb",
                        color="#ffffff",
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

        page.overlay.append(dlg_cal)
        dlg_cal.open = True
        render_cal()

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
                        "Belum ada data channel.\nSilakan input channel melalui aplikasi Desktop di PC Anda lalu tekan tombol Sinkron.",
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

            card = ft.Container(
                bgcolor="#18181b",
                border=ft.border.all(2, badge_color),
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
                    ft.Text(f"✉️ {email}", size=12, color="#a1a1aa"),
                    ft.Text(f"📝 {ket if ket else 'Tidak ada catatan'}", size=12, color="#71717a"),

                    ft.Divider(color="#27272a", height=8),

                    ft.Row([
                        ft.OutlinedButton(
                            text="📅 Pilih Kalender",
                            expand=True,
                            on_click=lambda e, cid=ch_id, nm=nama, lu=last_up: open_calendar_dialog(cid, nm, lu)
                        ),
                        ft.ElevatedButton(
                            text="⚡ Set Hari Ini",
                            bgcolor="#16a34a",
                            color="#ffffff",
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
            lbl_status_sync.value = "⚠️ Hubungkan Link Database terlebih dahulu"
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
            else:
                lbl_status_sync.value = f"❌ Gagal sinkron (HTTP {res.status_code})"
                lbl_status_sync.color = "#f87171"
                page.update()
        except Exception as err:
            lbl_status_sync.value = "❌ Gagal sinkron: Periksa koneksi internet"
            lbl_status_sync.color = "#f87171"
            show_snack(f"Error: {err}", "#dc2626")
            page.update()

    header_bar = ft.Container(
        bgcolor="#18181b",
        padding=14,
        content=ft.Column([
            ft.Row([
                ft.Text("▶ YT MANAGER MOBILE", size=17, weight=ft.FontWeight.BOLD, color="#ef4444"),
                ft.ElevatedButton(
                    text="🔄 Sinkron",
                    bgcolor="#2563eb",
                    color="#ffffff",
                    height=34,
                    on_click=sync_data
                )
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

            ft.Text(
                "ℹ️ Untuk mengetahui Link Database, silakan buka aplikasi Desktop di PC Anda.",
                size=11, color="#38bdf8", italic=True
            ),

            ft.Row([lbl_total_channel, lbl_status_sync], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True),

            ft.Container(
                bgcolor="#09090b",
                border=ft.border.all(1, "#27272a"),
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
                                ft.Text("Oranye: Upload (4–7 Hr)", size=10, color="#e4e4e7")
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
        ], spacing=5)
    )

    page.add(ft.Column([header_bar, list_cards], expand=True, spacing=0))
    sync_data()


if __name__ == "__main__":
    if hasattr(ft, "app"):
        ft.app(target=main)
    else:
        ft.run(main)
