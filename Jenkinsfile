pipeline {
    agent { label 'docker' }

    options {
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    environment {
        AWS_REGION         = 'ap-south-1'
        AWS_DEFAULT_REGION = 'ap-south-1'
        ECR_REPO           = 'pulsewatch'
        ECS_CLUSTER        = 'pulsewatch-cluster'
        ECS_SERVICE        = 'pulsewatch-task-service-0bws4d7k'
    }

    stages {
        /* stage('git checkout') {
            steps {
                git credentialsId: 'github',
                    url: 'https://github.com/NIHAL-TP/pulsewatch',
                    branch: 'main'
            }
        } */

        stage('prepare') {
            steps {
                script {
                    env.ACCOUNT_ID = sh(returnStdout: true,
                        script: 'aws sts get-caller-identity --query Account --output text').trim()
                    env.GIT_HASH   = sh(returnStdout: true,
                        script: 'git rev-parse --short HEAD').trim()
                    env.IMAGE_TAG  = "${env.GIT_HASH}-${env.BUILD_NUMBER}"
                    env.REGISTRY   = "${env.ACCOUNT_ID}.dkr.ecr.${env.AWS_REGION}.amazonaws.com"
                    env.IMAGE      = "${env.REGISTRY}/${env.ECR_REPO}:${env.IMAGE_TAG}"
                }
                echo "Image: ${env.IMAGE}"
            }
        }

        stage('docker build') {
            steps {
                sh 'docker build -t ${IMAGE} .'
            }
        }

        stage('smoke test') {
            steps {
                sh '''
                    docker run -d --name pw-${BUILD_NUMBER} ${IMAGE}
                    for i in $(seq 1 15); do
                        docker exec pw-${BUILD_NUMBER} python -c "import urllib.request as u; u.urlopen('http://localhost:5000/healthz')" && exit 0
                        sleep 2
                    done
                    echo "health check never succeeded"
                    docker logs pw-${BUILD_NUMBER}
                    exit 1
                '''
            }
        }

        stage('push to ecr') {
            steps {
                sh '''
                    aws ecr get-login-password --region ${AWS_REGION} \
                        | docker login --username AWS --password-stdin ${REGISTRY}
                    docker push ${IMAGE}
                '''
            }
        }
        stage('deploy to ecs') {
            steps {
                sh '''
                    set -e
                    sed "s|__IMAGE__|${IMAGE}|" ecs/taskdef.json > rendered-td.json
        
                    NEW_ARN=$(aws ecs register-task-definition --cli-input-json file://rendered-td.json \
                              --query 'taskDefinition.taskDefinitionArn' --output text)
                    echo "Registered: ${NEW_ARN}"
        
                    aws ecs update-service --cluster ${ECS_CLUSTER} --service ${ECS_SERVICE} \
                             --task-definition ${NEW_ARN}
                    aws ecs wait services-stable --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE}
					aws ecs wait services-stable --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE}

					# stable is not the same as "my version is running"
					CURRENT=$(aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} \
							--query 'services[0].taskDefinition' --output text)

					if [ "$CURRENT" != "$NEW_ARN" ]; then
						echo "DEPLOY FAILED: service is running $CURRENT but we deployed $NEW_ARN (rolled back?)"
						aws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} \
							--query 'services[0].events[:5].message' --output text
						STOPPED=$(   aws ecs list-tasks --cluster pulsewatch-cluster --desired-status STOPPED \
     						--query 'taskArns[:5]' --output text)
						[ -n "$STOPPED" ] && aws ecs describe-tasks --cluster ${ECS_CLUSTER} --tasks $STOPPED \
								--query 'tasks[].stoppedReason' --output textaws ecs describe-services --cluster ${ECS_CLUSTER} --services ${ECS_SERVICE} \
								--query 'services[0].deployments[].[status,rolloutState,rolloutStateReason,failedTasks,taskDefinition]' \
								--output text
						exit 1
					fi
					echo "Deploy verified: service is on $NEW_ARN"
                '''
            }
        }
    }

    post {
        always {
            sh '''
                docker rm -f pw-${BUILD_NUMBER} || true
                docker image rm -f ${IMAGE} || true
                docker logout ${REGISTRY} || true
            '''
        }
    }
}