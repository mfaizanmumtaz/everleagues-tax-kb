pipeline {
    agent any

    stages {
        stage('Deploy FastAPI Backend') {
            steps {
                echo 'Deploying FastAPI backend with uv and .venv'

                // Sync code to server
                sh '''
                rsync -avz --delete \
                  --exclude ".git" \
                  --exclude ".env" \
                  --exclude "Jenkinsfile" \
                  /var/lib/jenkins/workspace/eltaxdevsvcserver-py-be/ \
                  elaitaxdevadmin@4.193.192.34:/var/www/eltaxdevsvcserver-py-be/
                '''

                // SSH into server and handle venv + dependencies + restart
                sh '''
                ssh -o StrictHostKeyChecking=no elaitaxdevadmin@4.193.192.34 "
                  set -e
                  cd /var/www/eltaxdevsvcserver-py-be

                  # 2a️⃣ Ensure .venv exists
                  if [ ! -d .venv ]; then
                    uv venv .venv
                  fi

                  # 2b️⃣ Sync dependencies from uv.lock
                  uv sync

                  # 2c️⃣ Ensure gunicorn is installed
                  uv add gunicorn

                  # 2d️⃣ Restart FastAPI service via PM2 using .venv binary
                  pm2 restart eltaxdevsvcserver-py
                "
                '''
            }
        }
    }

    post {
        success {
            emailext(
                body: 'FastAPI Backend successfully deployed. Please verify API is working.',
                subject: '$PROJECT_NAME - Build #$BUILD_NUMBER - SUCCESS!',
                to: 'ghani.waheed@xevensolutions.com'
            )
        }
        failure {
            emailext(
                attachLog: true,
                body: 'FastAPI Backend deployment failed. Please check Jenkins logs.',
                subject: '$PROJECT_NAME - Build #$BUILD_NUMBER - FAILED!',
                to: 'ghani.waheed@xevensolutions.com'
            )
        }
    }
}


