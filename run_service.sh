export COMPOSE_HTTP_TIMEOUT=1200
export DOCKER_CLIENT_TIMEOUT=1200

RESTART_FLAG=0
BOOST=''
STAGE_FILE='ds_config_stage3.json'
per_device_train_batch_size=2
TRAIN_DATA=''
HF_TOKEN=''
SKIP=''
SERVER_IP='127.0.0.1'
TRAIN_CONTAINER='gpt-insight-model-llama2'
INFERENCE_CONTAINER='gpt-insight-inference-llama2'
INTERFACE_CONTAINER='gpt-insight-web-llama2'

while getopts i:d:b:t:s: flag
do
    case "$flag" in
        i) SERVER_IP=${OPTARG};;
        d) TRAIN_DATA=${OPTARG};;
        b) BOOST=${OPTARG};;
        t) HF_TOKEN=${OPTARG};;
        s) SKIP=${OPTARG};
    esac
done

if [ -n "$BOOST" ]
then
    echo "boost: $BOOST"
    echo "Use boost settings."
    STAGE_FILE='ds_config_stage2.json'
    per_device_train_batch_size=2
fi

if [[ $(lspci | grep -i nvidia) ]] && [[ ! $(nvidia-smi) ]];
then
    sudo add-apt-repository -y ppa:graphics-drivers
    sudo apt-get update
    sudo apt-get install -y nvidia-driver-520
    sudo apt-get -y install nvidia-cuda-toolkit
    if [ -f "/usr/share/X11/xorg.conf.d/10-nvidia.conf" ];
    then
        sudo > /usr/share/X11/xorg.conf.d/10-nvidia.conf
    fi
    sudo systemctl set-default multi-user.target
    RESTART_FLAG=1
elif [[ $(lspci | grep -i nvidia) ]];
then
    echo "nvidia driver and tool has been installed."
else
    echo "nvidia gpu is not detected. skip nvidia driver and tool install"
fi

if [[ ! $(docker --version) ]];
then
    sudo apt-get update -y
    sudo apt-get install -y apt-transport-https ca-certificates curl gnupg-agent software-properties-common
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
    sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu bionic stable"
    sudo apt-get update -y
    sudo apt-get install -y docker-ce
    sudo usermod -a -G docker $USER
    RESTART_FLAG=1
else
    echo "docker has been installed."
    docker network inspect nginx_network --format {{.Id}} >/dev/null 2>&1 || docker network create --driver bridge nginx_network
fi

if [[ $(lspci | grep -i nvidia) ]] && [[ ! $(nvidia-docker version) ]];
then
    curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
    distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
    curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
    sudo apt-get update -y
    sudo apt-get install -y nvidia-docker2
    sudo systemctl restart docker.service
    RESTART_FLAG=1
elif [[ $(lspci | grep -i nvidia) ]];
then
    echo "nvidia-docker has been installed."
else
    echo "nvidia gpu is not detected. skip nvidia-docker install"
fi

if [[ ! $(docker compose version) ]];
then
    sudo apt-get install -y docker-compose-plugin
else
    echo "docker compose has been installed."
fi

if [[ $RESTART_FLAG == 1 ]];
then
    sudo reboot
fi

base_path=$(pwd)
docker-compose -f $base_path/docker-compose.yml down

export HF_TOKEN=$HF_TOKEN

if [ -n "$TRAIN_DATA" ]
then
    cp $TRAIN_DATA $base_path/data/raw_data.xlsx
fi

if [[ ! $SKIP == "skip-train" ]]
then
    num_gpus=$(nvidia-smi --list-gpus | wc -l)
    gradient_accumulation_steps=$((128/$per_device_train_batch_size/$num_gpus))
    docker-compose -f $base_path/docker-compose.yml up -d $TRAIN_CONTAINER
    docker exec -it $TRAIN_CONTAINER bash -c "python3 preprocess.py \
            --data /data/raw_data.xlsx \
            --data_format llama \
            --output_dir /data \
            --max_len 4096"
    docker exec -it $TRAIN_CONTAINER bash -c "deepspeed --num_gpus=$num_gpus run_clm.py \
            --deepspeed $STAGE_FILE \
            --model_name_or_path yentinglin/Taiwan-LLaMa-v1.0 \
            --train_file /data/train.csv \
            --validation_file /data/validation.csv \
            --do_train \
            --do_eval \
            --bf16 \
            --overwrite_cache \
            --evaluation_strategy=steps \
            --output_dir /model/fine-tunning \
            --num_train_epochs 4  \
            --eval_steps 100 \
            --gradient_accumulation_steps $gradient_accumulation_steps \
            --per_device_train_batch_size $per_device_train_batch_size \
            --use_fast_tokenizer False \
            --learning_rate 5e-06 \
            --warmup_steps 10 \
            --save_total_limit 1 \
            --save_steps 100 \
            --save_strategy steps \
            --tokenizer_name yentinglin/Taiwan-LLaMa-v1.0 \
            --load_best_model_at_end=True \
            --block_size=4096 \
            --overwrite_output_dir"

    docker-compose -f $base_path/docker-compose.yml down
fi

if [[ ! $SKIP == "skip-inference" ]]
then
    echo "set server ip: $SERVER_IP"
    cp $base_path/build/interface/web/gpt_qa/template/main.js.temp $base_path/build/interface/web/gpt_qa/main.js
    sed -i "s/SERVER_IP/$SERVER_IP/g" $base_path/build/interface/web/gpt_qa/main.js
    docker-compose -f $base_path/docker-compose.yml up -d $INTERFACE_CONTAINER
    docker-compose -f $base_path/docker-compose.yml up -d $INFERENCE_CONTAINER
    echo "Please enter the URL link below into your browser to activate the dialog interface
        URL link: http://$SERVER_IP/gpt/qa/"
fi
unset HF_TOKEN
