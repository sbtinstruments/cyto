pipeline {
    agent any
    stages {
        stage('Install') {
            steps {
                sh 'poetry env use 3.8'
                sh 'poetry install'
            }
        }
        stage('Parallel') {
            parallel {
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
                        sh 'poetry run pylint cyto tests'
                    }
                stage('Type check') {
                    steps {
                        sh 'poetry run mypy .'
                    }
                }
            }
        }
    }
    post {
        always {
            junit 'junit-*.xml'
        }
    }
}
