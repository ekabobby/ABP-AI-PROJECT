import streamlit as st
import pandas as pd
import os
import altair as alt
from datetime import datetime
import io

# Nama file database
FILE_DATA = 'data_pembelian_obat.csv'

# --- 환율 정보 (Kurs Mata Uang) ---
# 이 환율은 예시이며, 필요시 최신 정보로 업데이트하세요.
RATES_TO_USD = {
    'USD': 1.0,
    'EUR': 1.07,
    'JPY': 0.0064,
    'KRW': 0.00072,
    'CNY': 0.13,
    'IDR': 0.000061
}

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="원료 의약품 가격 요약", layout="wide")
st.title("💊 의약품 원료 가격 요약 시스템")

# --- Fungsi-fungsi Helper ---
def load_data():
    if os.path.exists(FILE_DATA):
        return pd.read_csv(FILE_DATA, dtype={'품목코드': str})
    else:
        return pd.DataFrame(columns=['날짜', 'PO_번호', '품목코드', '품목명', '구매수량', '단위', '화폐', '단가', '총금액'])

def save_data(df):
    df.to_csv(FILE_DATA, index=False)

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='가격_분석')
        workbook = writer.book
        worksheet = writer.sheets['가격_분석']
        for i, col in enumerate(df.columns):
            column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, column_len)
    return output.getvalue()

# Fungsi konversi ke USD
def convert_to_usd(price, currency):
    """Mengkonversi harga dari mata uang asal ke USD."""
    rate = RATES_TO_USD.get(currency, 1.0)
    return price * rate

# --- BAGIAN 1: INPUT DATA (SIDEBAR) ---
st.sidebar.header("📝 새 거래 입력")
with st.sidebar.form("form_input"):
    tanggal = st.date_input("거래 날짜", datetime.now())
    nomer_po = st.text_input("PO 번호")
    kode_barang = st.text_input("품목코드", placeholder="예: RM-001")
    nama_barang = st.text_input("품목명 (원료)", placeholder="예: Paracetamol")
    
    col_qty, col_unit = st.columns([2, 1])
    with col_qty:
        jumlah = st.number_input("구매수량", min_value=0.0, step=1.0)
    with col_unit:
        satuan = st.text_input("단위", placeholder="kg/L")
    
    col_curr, col_price = st.columns([1, 2])
    with col_curr:
        mata_uang = st.selectbox("화폐", list(RATES_TO_USD.keys()))
    with col_price:
        harga_satuan = st.number_input("단가", min_value=0.0, format="%.2f")
    
    total_harga = jumlah * harga_satuan
    st.markdown(f"**총금액 (Total): {mata_uang} {total_harga:,.2f}**")
    
    submit_button = st.form_submit_button("데이터 저장")

    if submit_button:
        if nomer_po and kode_barang and nama_barang and harga_satuan > 0:
            df_lama = load_data()
            data_baru = {'날짜': [tanggal], 'PO_번호': [nomer_po], '품목코드': [kode_barang.upper().strip()], '품목명': [nama_barang.upper().strip()], '구매수량': [jumlah], '단위': [satuan.upper()], '화폐': [mata_uang], '단가': [harga_satuan], '총금액': [total_harga]}
            df_baru = pd.concat([df_lama, pd.DataFrame(data_baru)], ignore_index=True)
            save_data(df_baru)
            st.success(f"PO {nomer_po} ({nama_barang}) 저장되었습니다!")
            st.rerun()
        else:
            st.error("모든 정보를 입력해주세요! (품목코드 필수)")

# --- BAGIAN 1.5: IMPORT DATA EXCEL ---
st.sidebar.markdown("---")
with st.sidebar.expander("📂 Excel 파일에서 데이터 가져오기"):
    uploaded_file = st.file_uploader("Excel 파일을 선택하세요", type=['xlsx', 'xls'])
    if uploaded_file and st.button("데이터 처리 및 가져오기"):
        try:
            df_excel = pd.read_excel(uploaded_file)
            KOLOM_MAPPING = {'Tanggal PO': '날짜', 'Nomor PO': 'PO_번호', 'Kode Barang': '품목코드', 'Nama Barang': '품목명', 'Jumlah': '구매수량', 'Satuan': '단위', 'Mata Uang': '화폐', 'Harga Satuan': '단가'}
            df_excel.rename(columns=KOLOM_MAPPING, inplace=True)
            kolom_wajib = ['날짜', 'PO_번호', '품목코드', '품목명', '구매수량', '단가']
            if not all(kolom in df_excel.columns for kolom in kolom_wajib):
                missing = [k for k in kolom_wajib if k not in df_excel.columns]
                st.error(f"오류: 파일에 필요한 열이 없습니다: {', '.join(missing)}")
            else:
                df_excel['날짜'] = pd.to_datetime(df_excel['날짜'], errors='coerce')
                df_excel.dropna(subset=['날짜'], inplace=True)
                df_excel['품목코드'] = df_excel['품목코드'].astype(str).str.upper().str.strip()
                df_excel['품목명'] = df_excel['품목명'].str.upper().str.strip()
                if '단위' not in df_excel.columns: df_excel['단위'] = '-'
                if '화폐' not in df_excel.columns: df_excel['화폐'] = 'USD'
                df_excel['총금액'] = df_excel['구매수량'] * df_excel['단가']
                df_lama = load_data()
                for col in df_lama.columns:
                    if col not in df_excel.columns: df_excel[col] = None
                df_excel = df_excel[df_lama.columns]
                df_gabungan = pd.concat([df_lama, df_excel], ignore_index=True)
                df_gabungan.drop_duplicates(subset=['PO_번호', '품목코드'], keep='last', inplace=True)
                save_data(df_gabungan)
                st.success(f"{len(df_excel)}개의 데이터를 성공적으로 가져왔습니다!")
                st.rerun()
        except Exception as e:
            st.error(f"파일 처리 중 오류가 발생했습니다: {e}")

# --- BAGIAN UTAMA APLIKASI ---
df = load_data()

if not df.empty:
    df['날짜'] = pd.to_datetime(df['날짜'])
    
    tab1, tab2, tab3 = st.tabs(["📊 품목별 분석", "📅 월별 리포트", "📈 가격 추세"])
    
    with tab1:
        st.header("품목별 가격 등락 분석")
        list_kode = df['품목코드'].unique()
        analisis_data = []
        for kode in list_kode:
            df_barang = df[df['품목코드'] == kode].sort_values(by='날짜')
            nama_barang_display = df_barang.iloc[-1]['품목명']
            if len(df_barang) >= 2:
                transaksi_terakhir, transaksi_sebelumnya = df_barang.iloc[-1], df_barang.iloc[-2]
                curr_baru, curr_lama = transaksi_terakhir['화폐'], transaksi_sebelumnya['화폐']
                harga_baru, harga_lama = transaksi_terakhir['단가'], transaksi_sebelumnya['단가']
                if curr_baru == curr_lama:
                    selisih = harga_baru - harga_lama
                    persentase = (selisih / harga_lama) * 100 if harga_lama != 0 else 0
                    status = "단가 인상 🔺" if selisih > 0 else "단가 인하 🔻" if selisih < 0 else "유지 ➖"
                    selisih_text, persen_text = f"{selisih:,.2f}", f"{persentase:.2f}%"
                else:
                    status, selisih_text, persen_text = "💱 화폐 변경", "-", "-"
                analisis_data.append({'품목코드': kode, '품목명': nama_barang_display, '최근 거래일': transaksi_terakhir['날짜'].strftime('%Y-%m-%d'), '화폐': curr_baru, '최근 단가': harga_baru, '이전 단가': harga_lama, '차액': selisih_text, '변동률': persen_text, '상태': status, '최근 PO': transaksi_terakhir['PO_번호']})
            else:
                transaksi_terakhir = df_barang.iloc[-1]
                analisis_data.append({'품목코드': kode, '품목명': nama_barang_display, '최근 거래일': transaksi_terakhir['날짜'].strftime('%Y-%m-%d'), '화폐': transaksi_terakhir['화폐'], '최근 단가': transaksi_terakhir['단가'], '이전 단가': "-", '차액': "-", '변동률': "-", '상태': "신규 데이터", '최근 PO': transaksi_terakhir['PO_번호']})
        if analisis_data:
            df_analisis = pd.DataFrame(analisis_data)
            def highlight_status(val):
                color = 'red' if '인상' in val else 'green' if '인하' in val else 'orange' if '화폐' in val else 'black'
                return f'color: {color}; font-weight: bold'
            st.dataframe(df_analisis.style.applymap(highlight_status, subset=['상태']).format({'최근 단가': '{:,.2f}', '이전 단가': '{}'}), use_container_width=True)
            if st.download_button(label="📥 엑셀 보고서 다운로드", data=to_excel(df_analisis), file_name=f'가격_분석_{datetime.now().strftime("%Y%m%d")}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'): pass

    with tab2:
        st.header("📅 월별 재무 영향 리포트 (USD 기준)")
        df['Bulan_Tahun'] = df['날짜'].dt.to_period('M')
        list_bulan = df['Bulan_Tahun'].sort_values(ascending=False).unique()
        pilihan_bulan = st.selectbox("분석할 월 선택:", list_bulan)
        df_bulan_ini = df[df['Bulan_Tahun'] == pilihan_bulan]
        if not df_bulan_ini.empty:
            resume_data = []
            total_kenaikan_usd, total_penurunan_usd = 0, 0
            for kode in df_bulan_ini['품목코드'].unique():
                transaksi_akhir_bulan = df_bulan_ini[df_bulan_ini['품목코드'] == kode].sort_values(by='날짜').iloc[-1]
                df_sebelumnya = df[(df['품목코드'] == kode) & (df['날짜'] < transaksi_akhir_bulan['날짜'])].sort_values(by='날짜')
                if not df_sebelumnya.empty:
                    transaksi_lalu = df_sebelumnya.iloc[-1]
                    harga_usd_baru = convert_to_usd(transaksi_akhir_bulan['단가'], transaksi_akhir_bulan['화폐'])
                    harga_usd_lalu = convert_to_usd(transaksi_lalu['단가'], transaksi_lalu['화폐'])
                    selisih_harga_usd = harga_usd_baru - harga_usd_lalu
                    dampak_finansial_usd = selisih_harga_usd * transaksi_akhir_bulan['구매수량']
                    if dampak_finansial_usd != 0:
                        status = "단가 인상" if dampak_finansial_usd > 0 else "단가 인하"
                        resume_data.append({'품목코드': kode, '품목명': transaksi_akhir_bulan['품목명'], '원화폐': transaksi_akhir_bulan['화폐'], '재무 영향 (USD)': dampak_finansial_usd, '상태': status})
                        if dampak_finansial_usd > 0: total_kenaikan_usd += dampak_finansial_usd
                        else: total_penurunan_usd += abs(dampak_finansial_usd)
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📋 품목별 상세 내역")
                if resume_data:
                    df_resume = pd.DataFrame(resume_data)
                    st.dataframe(df_resume.style.format({'재무 영향 (USD)': '{:,.2f}'}), use_container_width=True)
                else:
                    st.info("이전 거래 대비 가격 변동이 없습니다.")
            with col2:
                st.subheader("📊 재무 영향 요약")
                st.metric("총 비용 증가 (USD)", f"{total_kenaikan_usd:,.2f}")
                st.metric("총 비용 절감 (USD)", f"{total_penurunan_usd:,.2f}", delta_color="inverse")
                net_impact = total_kenaikan_usd - total_penurunan_usd
                st.metric("순 영향 (USD)", f"{net_impact:,.2f}", delta=-net_impact)
                if resume_data:
                    chart_data = pd.DataFrame({'구분': ['비용 증가', '비용 감소'], '금액 (USD)': [total_kenaikan_usd, total_penurunan_usd]})
                    chart = alt.Chart(chart_data).mark_bar().encode(x='구분', y='금액 (USD)', color=alt.Color('구분', scale=alt.Scale(domain=['비용 증가', '비용 감소'], range=['#E74C3C', '#2ECC71'])))
                    st.altair_chart(chart, use_container_width=True)
        else:
            st.write("해당 월에 대한 데이터가 없습니다.")

    with tab3:
        st.header("📈 품목별 가격 변동 추세")
        col1, col2 = st.columns([1, 3])
        with col1:
            pilihan_display = st.selectbox("원료 선택:", df.drop_duplicates(subset=['품목코드'])['품목코드'] + " - " + df.drop_duplicates(subset=['품목코드'])['품목명'])
            pilihan_kode = pilihan_display.split(" - ")[0]
        with col2:
            df_grafik = df[df['품목코드'] == pilihan_kode].sort_values(by='날짜')
            if len(df_grafik) > 0:
                chart = alt.Chart(df_grafik).mark_line(point=True).encode(x=alt.X('날짜', axis=alt.Axis(format='%Y-%m-%d', title='거래 날짜')), y=alt.Y('단가', title='단가'), tooltip=['날짜', 'PO_번호', '화폐', '단가', '총금액']).properties(title=f"가격 기록: {pilihan_display}").interactive()
                st.altair_chart(chart, use_container_width=True)
            else:
                st.write("데이터가 충분하지 않습니다.")

    with st.expander("전체 데이터 기록 보기 (Raw Data)"):
        st.dataframe(df.sort_values(by='날짜', ascending=False).style.format({'단가': '{:,.2f}', '총금액': '{:,.2f}', '구매수량': '{:,.0f}'}), use_container_width=True)
else:
    st.info("데이터가 없습니다. 왼쪽 메뉴에서 데이터를 입력하거나 Excel 파일을 가져오세요.")
