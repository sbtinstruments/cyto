pipeline {
    agent any

    stages {
        stage('Test') {
            steps {
                sh 'python3 -m tox'
            }
        }
    }
}