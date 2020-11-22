pipeline {
    agent any
    stages {
        stage('All') {
            parallel {
                stage('Test') {
                    environment {
                        PYTEST_ARGS='--junitxml=junit-{envname}.xml'
                    }
                    steps {
                        sh 'python3 -m tox'
                    }
                }
                stage('In poetry virtualenv') {
                    stages {
                        stage('Install') {
                            steps {
                                sh 'poetry env use 3.8'
                                sh 'poetry install'
                            }
                        }
                        stage('Lint and check types') {
                            steps {
                                script {
                                    parallel([
                                        'Lint': { sh 'poetry run pylint cyto tests'},
                                        'Check types': { sh 'poetry run mypy .'}
                                    ])
                                }
                            }
                        }
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
