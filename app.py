from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from pandas import Timestamp
import os
from datetime import datetime
import locale
from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import or_


app = Flask(__name__)

# Set locale to Brazilian Portuguese
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Utility function for processing row values
def process_value(value):
    """Convert a value to a lowercase string and handle NaN or None."""
    return str(value).strip().lower() if pd.notna(value) else ''

def format_currency(value):
    """Format a value as Brazilian currency (R$)."""
    try:
        return locale.currency(value, grouping=True)
    except (TypeError, ValueError):
        return "R$ 0,00"

def format_date(value):
    """Format a date object or string as DD/MM/YYYY."""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    elif isinstance(value, str):
        try:
            date_obj = datetime.strptime(value, "%Y-%m-%d")
            return date_obj.strftime("%d/%m/%Y")
        except ValueError:
            return value
    return ""

def format_metric(value):
    """Format a metric value with proper separators and units."""
    try:
        return f"{value:,.2f} m²".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (TypeError, ValueError):
        return "0,00 m²"

# Define the Property model with all columns
class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sql = db.Column(db.String(50))  # N° do Cadastro (SQL)
    logradouro = db.Column(db.String(200))  # Nome do Logradouro
    numero = db.Column(db.String(50))  # Número
    complemento = db.Column(db.String(100))  # Complemento
    bairro = db.Column(db.String(100))  # Bairro
    matricula_imovel = db.Column(db.String(50))  # Matrícula do Imóvel
    referencia = db.Column(db.String(200))  # Referência
    cep = db.Column(db.String(20))  # CEP
    natureza_transacao = db.Column(db.String(100))  # Natureza de Transação
    valor_transacao = db.Column(db.Float)  # Valor de Transação
    data_transacao = db.Column(db.Date)  # Data de Transação
    valor_venal_referencia = db.Column(db.Float)  # Valor Venal de Referência
    proporcao_transmitida = db.Column(db.Float)  # Proporção Transmitida (%)
    valor_venal_proporcional = db.Column(db.Float)  # Valor Venal de Referência (proporcional)
    base_calculo = db.Column(db.Float)  # Base de Cálculo adotada
    tipo_financiamento = db.Column(db.String(100))  # Tipo de Financiamento
    valor_financiado = db.Column(db.Float)  # Valor Financiado
    cartorio_registro = db.Column(db.String(100))  # Cartório de Registro
    situacao_sql = db.Column(db.String(100))  # Situação do SQL
    area_terreno = db.Column(db.Float)  # Área do Terreno (m2)
    testada = db.Column(db.Float)  # Testada (m)
    fracao_ideal = db.Column(db.Float)  # Fração Ideal
    area_construida = db.Column(db.Float)  # Área Construída (m2)
    uso_iptu = db.Column(db.String(100))  # Uso (IPTU)
    descricao_uso_iptu = db.Column(db.String(200))  # Descrição do uso (IPTU)
    padrao_iptu = db.Column(db.String(100))  # Padrão (IPTU)
    descricao_padrao_iptu = db.Column(db.String(200))  # Descrição do padrão (IPTU)
    acc_iptu = db.Column(db.Float)  # ACC (IPTU)

# Reset the database (drops and recreates tables)
with app.app_context():
    db.drop_all()
    db.create_all()

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Check if a file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return "No file selected"
            if not file.filename.endswith('.xlsx'):
                return "Invalid file type. Please upload an Excel (.xlsx) file."

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            try:
                # Read Excel file and fetch sheet names
                excel_data = pd.ExcelFile(filepath, engine='openpyxl')
                sheet_names = excel_data.sheet_names

                # Render dropdown to select sheets
                return render_template('index.html', sheet_names=sheet_names, file_uploaded=True)
            except Exception as e:
                return f"<h2>Error processing file:</h2> {e}"

        # Process selected sheets
        if 'sheets' in request.form:
            selected_sheets = request.form.getlist('sheets')
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], os.listdir(app.config['UPLOAD_FOLDER'])[0])

            try:
                all_data = []
                for sheet in selected_sheets:
                    data = pd.read_excel(filepath, sheet_name=sheet, engine='openpyxl')
                    all_data.append(data)
                processed_data = pd.concat(all_data)

                # Process each row and add to database
                for _, row in processed_data.iterrows():
                    property_entry = Property(
                        sql=clean_string(row.get('N° do Cadastro (SQL)', '')),
                        logradouro=clean_string(row.get('Nome do Logradouro', '')),
                        numero=clean_string(row.get('Número', '')),
                        complemento=clean_string(row.get('Complemento', '')),
                        bairro=clean_string(row.get('Bairro', '')),
                        matricula_imovel=clean_string(row.get('Matrícula do Imóvel', '')),
                        referencia=clean_string(row.get('Referência', '')),
                        cep=clean_string(row.get('CEP', '')),
                        natureza_transacao=clean_string(row.get('Natureza de Transação', '')),
                        valor_transacao=convert_to_float(row.get('Valor de Transação (declarado pelo contribuinte)', 0)),
                        data_transacao=parse_date(row.get('Data de Transação', '')),
                        valor_venal_referencia=convert_to_float(row.get('Valor Venal de Referência', 0)),
                        proporcao_transmitida=convert_to_float(row.get('Proporção Transmitida (%)', 0)),
                        valor_venal_proporcional=convert_to_float(row.get('Valor Venal de Referência (proporcional)', 0)),
                        base_calculo=convert_to_float(row.get('Base de Cálculo adotada', 0)),
                        tipo_financiamento=clean_string(row.get('Tipo de Financiamento', '')),
                        valor_financiado=convert_to_float(row.get('Valor Financiado', 0)),
                        cartorio_registro=clean_string(row.get('Cartório de Registro', '')),
                        situacao_sql=clean_string(row.get('Situação do SQL', '')),
                        area_terreno=convert_to_float(row.get('Área do Terreno (m2)', 0)),
                        testada=convert_to_float(row.get('Testada (m)', 0)),
                        fracao_ideal=convert_to_float(row.get('Fração Ideal', 0)),
                        area_construida=convert_to_float(row.get('Área Construída (m2)', 0)),
                        uso_iptu=clean_string(row.get('Uso (IPTU)', '')),
                        descricao_uso_iptu=clean_string(row.get('Descrição do uso (IPTU)', '')),
                        padrao_iptu=clean_string(row.get('Padrão (IPTU)', '')),
                        descricao_padrao_iptu=clean_string(row.get('Descrição do padrão (IPTU)', '')),
                        acc_iptu=convert_to_float(row.get('ACC (IPTU)', 0)),
                    )
                    db.session.add(property_entry)

                db.session.commit()
                return redirect(url_for('search'))  # Redirect to the search page

            except Exception as e:
                return f"<h2>Error processing sheets:</h2> {e}"

    return render_template('index.html')

# Move these functions outside the route handler
def convert_to_float(value):
    """Convert values to float safely, return 0.0 if conversion fails."""
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return 0.0  # Default value if conversion fails

def clean_string(value):
    """Convert non-numeric values to lowercase and strip spaces."""
    return str(value).strip().lower() if pd.notna(value) else ''

def parse_date(value):
    """Try parsing different date formats and return a date object."""
    if pd.isna(value) or value == '':
        return None

    if isinstance(value, pd.Timestamp):
        return value.date()  # Convert pandas Timestamp to date

    date_formats = ["%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(str(value), fmt).date()
        except ValueError:
            continue

    return None  # Return None if no format matched

@app.route('/search')
def search():
    query = request.args.get('q', '').strip().lower()
    if query:
        results = Property.query.filter(
            (Property.sql.ilike(f"%{query}%")) |
            (Property.logradouro.ilike(f"%{query}%")) |
            (Property.numero.ilike(f"%{query}%")) |
            (Property.complemento.ilike(f"%{query}%")) |
            (Property.bairro.ilike(f"%{query}%")) |
            (Property.matricula_imovel.ilike(f"%{query}%"))
        ).all()
    else:
        results = []
    
    return render_template('search.html', results=results, query=query)

@app.route('/property/<int:property_id>', methods=['GET'])
def property_detail(property_id):
    # Fetch property by ID
    property_data = Property.query.get_or_404(property_id)
    return render_template('property_detail.html', property=property_data)

# Custom template filters
@app.template_filter('currency')
def currency_filter(value):
    return format_currency(value)

@app.template_filter('date')
def date_filter(value):
    return format_date(value)

@app.template_filter('metric')
def metric_filter(value):
    return format_metric(value)

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q', '').strip().lower()
    if query:
        results = Property.query.filter(Property.logradouro.ilike(f"%{query}%")).limit(10).all()
        suggestions = [prop.logradouro for prop in results]
        return jsonify(suggestions)
    return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)


