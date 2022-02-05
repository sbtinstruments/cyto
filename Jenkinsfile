pipeline {
    agent {
        dockerfile {
            filename 'Dockerfile.build'
        }
    }
    stages {
        stage('Install') {
            steps {
                // Install all extras along with the dependencies in
                // poetry's virtual environment.
                sh 'poetry install --extras all'
            }
        }
        stage('Quality Assurance') {
            parallel {
                stage('Test') {
                    environment {
                        // The spinner interferes with Jenkins' output parsing.
                        TOX_PARALLEL_NO_SPINNER=1
                        // Generate JUnit XML files that Jenkins can parse in a
                        // post section (see [1]).
                        PYTEST_ARGS='--junitxml=junit-{envname}.xml'
                    }
                    stages {
                        stage('pytest') {
                            environment {
                                // We skip the coverage step for now. We run this in
                                // test environment later in its own stage.
                                TOX_SKIP_ENV='coverage'
                            }
                            steps {
                                // Note that we don't do "poetry run tox". This is because
                                // tox manages its own virtual environments. See the
                                // [tool.tox] section in pyproject.toml for details.
                                sh 'python3 -m tox --parallel'
                            }
                            post {
                                always {
                                    // Parse JUnit XML files
                                    junit 'junit-*.xml'  // [1]
                                }
                            }
                        }
                        stage('coverage') {
                            steps {
                                // Note that we don't do "poetry run tox". This is because
                                // tox manages its own virtual environments. See the
                                // [tool.tox] section in pyproject.toml for details.
                                sh 'python3 -m tox --parallel -e coverage'
                            }
                            post {
                                always {
                                    // Publish the HTML coverage report
                                    publishHTML target: [
                                        // Report may be missing if one of the tests fail
                                        allowMissing: true,
                                        alwaysLinkToLastBuild: true,
                                        keepAll: true,
                                        reportDir: 'htmlcov',
                                        reportFiles: 'index.html',
                                        reportName: 'Test Coverage Report'
                                    ]
                                }
                            }
                        }
                    }
                }
                stage('Lint') {
                    steps {
                        sh 'poetry run task pylint'
                    }
                }
                stage('Check types') {
                    steps {
                        sh 'poetry run task mypy'
                    }
                }
                stage('Check formatting') {
                    steps {
                        sh 'poetry run task black --check'
                    }
                }
                stage('Check import order') {
                    steps {
                        sh 'poetry run task isort --check'
                    }
                }
            }
        }
        stage('Build') {
            steps {
                sh 'poetry build'
            }
        }
    }
    post {
        failure {
            // Notify slack if anything went wrong
            slackSend(color: '#FF9FA1', message: "`${env.JOB_NAME}` has failed CI:\n${env.BUILD_URL}")
        }
    }
}
