import os
from os.path import join, dirname
from dotenv import load_dotenv
from flask import Flask, request, jsonify, redirect, render_template
from neo4j import GraphDatabase

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

URI = os.environ.get("URI")
USERNAME = os.environ.get("UNAME")
PASSWORD = os.environ.get("PASSWORD")

driver = GraphDatabase.driver(uri=URI, auth=(USERNAME, PASSWORD))
api = Flask(__name__)
driver.verify_connectivity()


def get_employees(tx):
    locate_employees = "MATCH (employee:Employee) RETURN employee"
    locate_employees_result = tx.run(locate_employees).data()
    employees = [{
        'name': result['employee']['name'],
        'occupation': result['employee']['occupation']
    } for result in locate_employees_result]
    return employees


@api.route('/employees', methods=['GET'])
def get_employees_route():
    with driver.session() as session:
        employees = session.read_transaction(get_employees)

    response = {'employees': employees}
    return jsonify(response)


def get_employee(tx, name):
    locate_employee = "MATCH (employee:Employee {name: $name}) RETURN employee"
    locate_employee_result = tx.run(locate_employee, name=name).data()

    if locate_employee_result:
        return {
            'name': locate_employee_result[0]['employee']['name'],
            'occupation': locate_employee_result[0]['employee']['occupation']
        }


@api.route('/employees/name', methods=['GET'])
def get_employee_route():
    name = request.json['name']

    with driver.session() as session:
        employee = session.read_transaction(get_employee, name)

    if not employee:
        response = {'message': 'Employee not found!'}
        return jsonify(response)
    else:
        response = {'employee': employee}
        return jsonify(response)


def get_employees_by_occupation(tx, occupation):
    locate_employees = "MATCH (employee:Employee {occupation: $occupation}) RETURN employee"
    locate_employees_result = tx.run(locate_employees, occupation=occupation).data()
    employees = [{
        'name': result['employee']['name'],
        'occupation': result['employee']['occupation']
    } for result in locate_employees_result]
    return employees


@api.route('/employees/occupation', methods=['GET'])
def get_employees_by_occupation_route():
    occupation = request.json['occupation']

    with driver.session() as session:
        employees = session.read_transaction(get_employees_by_occupation, occupation)

    response = {'employees': employees}
    return jsonify(response)


def add_employee(tx, name, occupation, department):
    locate_employee_with_name = "MATCH (employee:Employee {name: $name}) RETURN employee"
    locate_employee_with_name_result = tx.run(locate_employee_with_name, name=name).data()

    locate_department = "MATCH (department:Department {name: $department}) RETURN department"
    locate_department_result = tx.run(locate_department, department=department).data()

    if not locate_employee_with_name_result and locate_department_result:
        create_employee = """
            MATCH (department:Department {name: $department})
            WITH department
            CREATE (:Employee {name: $name, occupation: $occupation})-[:WORKS_IN]->(department)
        """
        tx.run(create_employee, name=name, occupation=occupation, department=department)
        return {'name': name, 'occupation': occupation, 'department': department}


@api.route('/employees', methods=['POST'])
def add_employee_route():
    name = request.json['name']
    occupation = request.json['occupation']
    department = request.json['department']

    with driver.session() as session:
        session.write_transaction(add_employee, name, occupation, department)

    response = {'status': 'success'}
    return jsonify(response)


def update_employee(tx, id, name, occupation, department):
    locate_employee = "MATCH (employee:Employee) WHERE ID(employee) = $id RETURN employee"
    locate_employee_result = tx.run(locate_employee, id=id).data()

    locate_department = "MATCH (department:Department {name: $department}) RETURN department"
    locate_department_result = tx.run(locate_department, department=department).data()

    if locate_employee_result and locate_department_result:
        delete_employee = "MATCH (employee:Employee) WHERE ID(employee) = $id DETACH DELETE employee"
        tx.run(delete_employee, id=id)
    else:
        return None

    locate_name = "MATCH (employee:Employee {name: $name}) RETURN employee"
    locate_name_result = tx.run(locate_name, name=name).data()

    if not locate_name_result:
        create_employee = """
            MATCH (department:Department {name: $department})
            WITH department
            CREATE (:Employee {name: $name, occupation: $occupation})-[:WORKS_IN]->(department)
        """
        tx.run(create_employee, name=name, occupation=occupation, department=department)
        return {'name': name, 'occupation': occupation, 'department': department}


@api.route('/employees/<int:id>', methods=['PUT'])
def update_employee_route(id):
    name = request.json['name']
    occupation = request.json['occupation']
    department = request.json['department']

    with driver.session() as session:
        employee = session.write_transaction(update_employee, id, name, occupation, department)

    if not employee:
        response = {'message': 'Invalid parameters!'}
        return jsonify(response)
    else:
        response = {'status': 'success'}
        return jsonify(response)


def delete_employee(tx, id):
    locate_connection = """
        MATCH (employee:Employee)-[conn]->(:Department)
        WHERE ID(employee) = $id
        WITH TYPE(conn) AS connection
        RETURN connection
    """
    locate_connection_result = tx.run(locate_connection, id=id).data()

    if locate_connection_result[0]['connection'] == 'MANAGES':
        del_employee = """
            MATCH (employee:Employee)-[:MANAGES]->(department:Department)
            WHERE ID(employee) = $id
            DETACH DELETE employee, department
        """
        tx.run(del_employee, id=id)
        return {'status': 'success'}
    else:
        del_employee = "MATCH (employee:Employee) WHERE ID(employee) = $id DETACH DELETE employee"
        tx.run(del_employee, id=id)
        return {'status': 'success'}


@api.route('/employees/<int:id>', methods=['DELETE'])
def delete_employee_route(id):
    with driver.session() as session:
        employee = session.write_transaction(delete_employee, id)

    if not employee:
        response = {'message': 'Employee not found!'}
        return jsonify(response)
    else:
        response = {'status': 'success'}
        return jsonify(response)


def get_subordinates(tx, id):
    locate_employee = "MATCH (employee:Employee) WHERE ID(employee) = $id RETURN employee"
    locate_employee_result = tx.run(locate_employee, id=id).data()

    if not locate_employee_result:
        return None
    else:
        locate_subordinates = """
            MATCH (employee:Employee)-[:MANAGES]->(subordinate:Employee)
            WHERE ID(employee) = $id
            RETURN subordinate
        """
        locate_subordinates_result = tx.run(locate_subordinates, id=id).data()
        subordinates = [{
            'name': result['subordinate']['name'],
            'occupation': result['subordinate']['occupation']
        } for result in locate_subordinates_result]
        return subordinates


@api.route('/employees/<int:id>/subordinates', methods=['GET'])
def get_subordinates_route(id):
    with driver.session() as session:
        subordinates = session.read_transaction(get_subordinates, id)

    response = {'subordinates': subordinates}
    return jsonify(response)


if __name__ == '__main__':
    api.run()
