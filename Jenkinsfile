pipeline {
    agent any
    stages {
        stage('Test') {
            environment {
                PYTEST_ARGS='--junitxml=junit-{envname}.xml'
            }
            steps {
                sh 'python3 -m tox'
            }
        }
        stage('Lint') {
            steps {
                sh 'poetry install'
                sh 'poetry run pylint cyto tests'
            }
        }
        stage('Check types') {
            steps {
                sh 'poetry install'
                sh 'poetry run mypy .'
            }
        }
    }
    post {
        always {
            junit 'junit-*.xml'
        }
    }
}
