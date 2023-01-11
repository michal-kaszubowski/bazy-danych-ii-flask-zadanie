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


def add_department(tx, name):
    locate_department = "MATCH (department:Department {name: $name}) RETURN department"
    locate_department_result = tx.run(locate_department, name=name).data()

    if locate_department_result:
        return None
    else:
        create_department = "CREATE (department:Department {name: $name}) RETURN department"
        department = tx.run(create_department, name=name)
        return department


@api.route('/departments', methods=['POST'])
def add_department_route():
    name = request.json['name']

    with driver.session() as session:
        department = session.write_transaction(add_department, name)

    if not department:
        response = {'message': 'Department already exists!'}
        return jsonify(response), 400
    else:
        response = {'status': 'success'}
        return jsonify(response)


def add_employee(tx, name, works_in):
    locate_employee = "MATCH (employee:Employee {name: $name}) RETURN employee"
    locate_employee_result = tx.run(locate_employee, name=name)

    locate_department = "MATCH (department:Department {name: $works_in}) RETURN department"
    locate_department_result = tx.run(locate_department, works_in=works_in)

    if not locate_employee_result and locate_department_result:
        create_employee = """
            MATCH (department:Department {name: $works_in})
            CREATE (employee:Employee {name: $name})-[:WORKS_IN]->(department),
            (employee)<-[:MANAGES]-(department)
            RETURN employee
        """
        employee = tx.run(create_employee, name=name, works_in=works_in)
        return employee
    else:
        return None


@api.route('/employees', methods=['POST'])
def add_employee_route():
    name = request.json['name']
    works_in = request.json['works_in']

    with driver.session() as session:
        employee = session.write_transaction(add_employee, name, works_in)

    if not employee:
        response = {'message': "Employee exists or Department doesn't!"}
        return jsonify(response), 400
    else:
        response = {'status': 'success'}
        return jsonify(response)


if __name__ == '__main__':
    api.run()
