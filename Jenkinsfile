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
                            parallel {
                                stage('Lint') {
                                    steps {
                                        sh 'poetry run pylint cyto tests'
                                    }
                                }
                                stage('Check types') {
                                    steps {
                                        sh 'poetry run mypy .'
                                    }
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
