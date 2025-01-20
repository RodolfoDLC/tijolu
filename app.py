from flask import Flask, render_template, request, redirect, url_for, flash, json
from flask_sqlalchemy import SQLAlchemy
import pandas as pd
from pandas import Timestamp
import os
from datetime import datetime
import locale
from flask import Flask, render_template, request, redirect, url_for, jsonify
from sqlalchemy import or_, case, and_, func
from sqlalchemy.ext.hybrid import hybrid_property
from collections import defaultdict


app = Flask(__name__)
app.secret_key = os.urandom(24)

# Set locale to Brazilian Portuguese
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///properties.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
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

    @hybrid_property
    def preco_m2(self):
        """Calculate price per square meter based on property type and conditions"""
        if (self.proporcao_transmitida == 100 and 
            self.natureza_transacao and 
            'compra e venda' in self.natureza_transacao.lower() and 
            self.valor_transacao):
            
            if self.uso_iptu == '000' and self.area_terreno:  # For land
                return round(self.valor_transacao / self.area_terreno, 2)
            elif self.area_construida and self.area_construida > 0:  # For buildings
                return round(self.valor_transacao / self.area_construida, 2)
        
        return None

    @preco_m2.expression
    def preco_m2(cls):
        """SQL expression for price per square meter calculation"""
        return case(
            (and_(
                cls.proporcao_transmitida == 100,
                cls.natureza_transacao.ilike('%compra e venda%'),
                cls.valor_transacao.isnot(None),
                cls.uso_iptu == '000',
                cls.area_terreno.isnot(None),
                cls.area_terreno > 0
            ), cls.valor_transacao / cls.area_terreno),
            (and_(
                cls.proporcao_transmitida == 100,
                cls.natureza_transacao.ilike('%compra e venda%'),
                cls.valor_transacao.isnot(None),
                cls.area_construida.isnot(None),
                cls.area_construida > 0
            ), cls.valor_transacao / cls.area_construida),
            else_=None
        )

# Only create tables if they don't exist
with app.app_context():
    db.create_all()

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        # Check if a file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                flash("Nenhum arquivo selecionado", "error")
                return redirect(url_for('home'))
            if not file.filename.endswith('.xlsx'):
                flash("Tipo de arquivo inválido. Por favor, envie um arquivo Excel (.xlsx)", "error")
                return redirect(url_for('home'))

            # Create upload folder if it doesn't exist
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])

            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)

            try:
                # Read Excel file and fetch sheet names
                excel_data = pd.ExcelFile(filepath, engine='openpyxl')
                sheet_names = excel_data.sheet_names
                return render_template('index.html', sheet_names=sheet_names)
            except Exception as e:
                flash(f"Erro ao processar arquivo: {str(e)}", "error")
                return redirect(url_for('home'))

        # Process selected sheets
        if 'sheets' in request.form:
            selected_sheets = request.form.getlist('sheets')
            if not selected_sheets:
                flash("Por favor, selecione pelo menos uma aba", "error")
                return redirect(url_for('home'))

            try:
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], os.listdir(app.config['UPLOAD_FOLDER'])[0])
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
                        cep=format_cep(row.get('CEP', '')),
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
                flash("Dados importados com sucesso!", "success")
                return redirect(url_for('search'))

            except Exception as e:
                flash(f"Erro ao processar planilhas: {str(e)}", "error")
                return redirect(url_for('home'))

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

def format_cep(value):
    """Format CEP to ensure 8 digits with leading zeros."""
    if pd.isna(value):
        return ''
    
    # Remove any non-numeric characters
    cep = ''.join(filter(str.isdigit, str(value)))
    
    # Pad with leading zeros if necessary
    cep = cep.zfill(8)
    
    return cep

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
    results = []
    
    if query:
        try:
            results = Property.query.filter(
                (Property.sql.ilike(f"%{query}%")) |
                (Property.logradouro.ilike(f"%{query}%")) |
                (Property.cep.ilike(f"%{query}%")) |
               (Property.bairro.ilike(f"%{query}%")) |
                (Property.matricula_imovel.ilike(f"%{query}%"))
            ).all()
        except Exception as e:
            print(f"Error in search: {e}")
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

def capitalize_pt_br(text):
    """
    Capitalize text following Brazilian Portuguese rules.
    Handles numbers and dots in the text.
    """
    if not text:
        return ''
    
    # List of words that should remain lowercase
    lowercase_words = {'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'com', 'para', 'por', 'a', 'o', 'as', 'os', 'um', 'uma', 'uns', 'umas', 'no', 'na', 'nos', 'nas'}
    
    # List of known abbreviations that should remain uppercase
    abbreviations = {'sql', 'cep', 'acc', 'iptu'}
    
    # Special case mappings for specific terms
    special_cases = {
        'compra e venda': 'Compra e Venda',
        'permuta': 'Permuta',
        'doacao': 'Doação',
        'dacao em pagamento': 'Dação em Pagamento',
        'arrematacao': 'Arrematação',
        'adjudicacao': 'Adjudicação',
        'sem financiamento': 'Sem Financiamento',
        'financiamento bancario': 'Financiamento Bancário',
        'financiamento imobiliario': 'Financiamento Imobiliário',
        'carta de credito': 'Carta de Crédito',
        'consorcio': 'Consórcio',
        'financiamento proprio': 'Financiamento Próprio'
    }
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Extract any leading numbers and dots
    import re
    prefix_match = re.match(r'^(\d+\.\s*)?(.+)$', text)
    if prefix_match:
        prefix = prefix_match.group(1) or ''
        main_text = prefix_match.group(2)
    else:
        prefix = ''
        main_text = text
    
    # Check for special cases first
    main_text_lower = main_text.lower()
    if main_text_lower in special_cases:
        return prefix + special_cases[main_text_lower]
    
    words = main_text.split()
    capitalized_words = []
    
    for i, word in enumerate(words):
        word_lower = word.lower()
        
        # Keep abbreviations in uppercase
        if word_lower in abbreviations:
            capitalized_words.append(word_lower.upper())
            continue
            
        # Always capitalize first word
        if i == 0:
            capitalized_words.append(word.capitalize())
            continue
            
        # Keep lowercase words if they're not at the start
        if word_lower in lowercase_words:
            capitalized_words.append(word_lower)
            continue
            
        # Capitalize other words
        capitalized_words.append(word.capitalize())
    
    # Combine prefix with capitalized text
    return prefix + ' '.join(capitalized_words)

# Register the filter with Jinja2
app.jinja_env.filters['capitalize_pt_br'] = capitalize_pt_br

if __name__ == '__main__':
    app.run(debug=True)


