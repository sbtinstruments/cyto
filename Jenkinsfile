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
    }
}
