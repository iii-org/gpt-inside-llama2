if [[ $(docker compose version) ]];
then
    base_path=$(dirname "$0")
    docker-compose -f $base_path/docker-compose.yml down
fi
