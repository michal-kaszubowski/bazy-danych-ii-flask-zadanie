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


if __name__ == '__main__':
    api.run()
