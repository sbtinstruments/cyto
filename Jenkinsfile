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
                            environment {
                                // Get total coverage for the badge
                                TOTAL_COVERAGE=sh(script: 'poetry run coverage report | grep TOTAL | awk \'{print $4 "\\t"}\'', returnStdout: true).trim()
                            }
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
                                    addShortText text: "Coverage: ${env.TOTAL_COVERAGE}"
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
}
