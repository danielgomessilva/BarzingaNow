import json
import datetime

from flask import Blueprint, request, session
from google.appengine.ext import ndb

from transaction.model import Transaction, TransactionItem
from user.model import User
from product.model import Product

transaction = Blueprint('transaction', __name__)

@transaction.route('/', methods=['GET'])
def get_all():
    transactions = [t.to_dict() for t in Transaction.query().fetch()]
    return json.dumps(transactions)

@transaction.route('/<int:transaction_id>', methods=['GET'])
def get_by_id(transaction_id):
    transaction = Transaction.get_by_id(transaction_id)

    if not transaction:
        return 'Transaction id %s not found' % (transaction_id), 404

    return json.dumps(transaction.to_dict())

@transaction.route('/', methods=['POST'])
def add():
    logged_user = session['barzinga_user']
    logged_user = User.query().filter(User.email == logged_user["email"]).get()

    products = json.loads(request.form['products'])

    products_list = []
    quantity_table = {}

    for product in products:
        quantity_table[product['id']] = product['quantity']
        products_list.append(ndb.Key(Product, product['id']).get())

    print products_list

    try:
        transaction = Transaction.new(logged_user, products_list, quantity_table)
        transaction.put()
    except Exception as e:
        return str(e), 400

    return '', 204

@transaction.route('/app', methods=['POST'])
def add_app():

    json_data = request.get_json()

    user_json = json_data.get('user')

    # user_pin = json_data.get('pin')

    print user_json.get('email')

    user = User.query().filter(User.email == user_json.get('email')).get()

    products = json_data.get('products')

    # if user_pin != user.pin :
    #     return str('Pin Invalido'), 303

    products_list = []
    quantity_table = {}

    for product in products:
        quantity_table[product['id']] = product['quantity']
        products_list.append(ndb.Key(Product, product['id']).get())

    print products_list

    try:
        transaction = Transaction.new(user, products_list, quantity_table)
        transaction.put()
    except Exception as e:
        return str(e), 400

    return str('ok'), 200

@transaction.route('/extract', methods=['GET'])
def transactions_user():
    logged_user = session['barzinga_user']
    logged_user = User.query().filter(User.email == logged_user["email"]).get()

    transactions = Transaction.query().filter(Transaction.user == logged_user.key).order(-Transaction.date).fetch(20)

    trans = [];

    for t in transactions:
        transa = {}
        transa['id'] = str(t.key)
        transa['user'] = logged_user.name.encode('utf-8').strip()
        transa['value'] = str(t.value)
        transa['date'] = str(t.date.strftime('%d/%m/%y - %H:%M'))
        itens = []
        for it in t.items :
            item = {}
            transaction_item = it.get()

            prod = transaction_item.product.get()
            item['product'] = 'Nao Existe Mais'

            if prod:
                item['product'] = prod.description


            item['quantity'] = str(transaction_item.quantity)
            itens.append(item)

        transa['itens'] = itens
        trans.append(transa)

    return json.dumps(trans)


@transaction.route('/extract_all', methods=['GET'])
def transactions_alll():
    transactions = Transaction.query().fetch()

    trans = [];

    for t in transactions:
        transa = {}
        transa['id'] = str(t.key)
        transa['user'] = t.user.get().name.encode('utf-8').strip()
        transa['value'] = str(t.value)
        transa['date'] = str(t.date)
        itens = []
        for it in t.items :
            item = {}
            transaction_item = it.get()
            item['product'] = transaction_item.product.get().description
            item['quantity'] = transaction_item.quantity
            itens.append(item)

        transa['itens'] = itens
        trans.append(transa)

    return json.dumps(trans)

@transaction.route('/transactions_all/<string:start>/<string:end>', methods=['GET'], strict_slashes=True)
def transactions_all(start=None, end=None):
    if start is None or end is None:
        transactions = Transaction.query().fetch()
    else:
        splitStart = start.split('-')
        from_date = datetime.datetime(year=int(splitStart[2]), month=int(splitStart[1]), day=int(splitStart[0]))
        splitEnd = end.split('-')
        to_date = datetime.datetime(year=int(splitEnd[2]), month=int(splitEnd[1]), day=int(splitEnd[0]))

        transactions = Transaction.query().filter(Transaction.date <= to_date, Transaction.date >= from_date).fetch()

    transactionsJson = [];
    for t in transactions:
        transactionJson = {}
        if t.date is not None:
            transactionJson['date'] = str(t.date.strftime('%d/%m/%y - %H:%M'))
        else:
            transactionJson['date'] = ''
        transactionJson['value'] = str(t.value)
        transactionJson['user'] = str(t.user.get().email).split('@')[0]
        itensJson = [];
        for i in t.items:
            itemJson = {}
            transaction_item = i.get()
            prod = transaction_item.product.get()
            itemJson['product'] = 'Nao Existe Mais'

            if prod :
                itemJson['product'] = prod.description

            itemJson['quantity'] = transaction_item.quantity
            itensJson.append(itemJson)
            
        transactionJson["itens"] = itensJson
        transactionsJson.append(transactionJson)

    return json.dumps(transactionsJson)

@transaction.route('/sumarize/', methods=['GET'])
def sumarize_all():
    transactions = Transaction.query().fetch()
    value =  0
    for t in transactions:
        value +=t.value

    return json.dumps(value)

@transaction.route('/sum/<string:start>/<string:end>', methods=['GET'], strict_slashes=True)
def sum_value(start=None, end=None):

    if start is None or end is None:
        return 'No start or end date use: sum/01-01-1970/02-02-1970', 404
    else:
        splitStart = start.split('-')
        from_date = datetime.datetime(year=int(splitStart[2]), month=int(splitStart[1]), day=int(splitStart[0]))
        splitEnd = end.split('-')
        to_date = datetime.datetime(year=int(splitEnd[2]), month=int(splitEnd[1]), day=int(splitEnd[0]))

        transactions = Transaction.query().filter(Transaction.date <= to_date, Transaction.date >= from_date).fetch()

    value =  0
    for t in transactions:
        value +=t.value

    return json.dumps(value)

@transaction.route('/dispatch', methods=['GET'])
def dispatch_task():
    from google.appengine.api import taskqueue
    task = taskqueue.add(url='/api/transaction/post_recommender')
    return str(task), 200

@transaction.route('/post_recommender', methods=['POST'])
def post_recommender_task():
    transactions = Transaction.query().fetch()

    for t in transactions:
        user = t.user.get()
        for it in t.items :
            transaction_item = it.get()
            product = transaction_item.product.get()

            params = {'user_id': user.key.id(), 'item_id': product.key.id(), 'app_cod': 'BZG'}
            execute_post(params)

    return '', 200

def execute_post(params):
    url = 'http://recomendador-dot-relacionadosites-qa.appspot.com/api/register_access'

    import urllib
    from google.appengine.api import urlfetch

    data = json.dumps(params)

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    result = urlfetch.fetch(
        url=url,
        payload=data,
        method=urlfetch.POST,
        headers=headers)

    print result.content
