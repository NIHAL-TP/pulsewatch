pipeline {
	agent { label 'docker' }
	stages {
		stage('git checkout') {
			steps {
				git credentialsId: 'github', 
       				url: 'https://github.com/NIHAL-TP/pulsewatch',
       				branch: 'main'
				}
		}
	}
}
