import os
from kubernetes import client, config, watch
from kubernetes.client.exceptions import ApiException

config.load_kube_config()

core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()
custom_api = client.CustomObjectsApi()

GROUP = "podinfo.interview.assignment"
VERSION = "v1alpha1"
PLURAL = "myappresources"
NAMESPACE = "default"


def create_redis_secret(namespace):
    secret = client.V1Secret(
        metadata=client.V1ObjectMeta(name='redis-password'),
        string_data={'password': 'your-secure-password'}
    )
    try:
        core_v1.create_namespaced_secret(namespace, secret)
        print("Secret created successfully")
    except ApiException as e:
        if e.status == 409:
            print("Secret already exists, skipping creation")
        else:
            print("Error creating secret:", e)


def create_podinfo_deployment(spec, namespace):
    env_vars = [client.V1EnvVar(name=e['name'], value=e['value']) for e in spec['env']]
    env_vars.append(client.V1EnvVar(name='PODINFO_UI_COLOR', value=spec['ui']['color']))
    env_vars.append(client.V1EnvVar(name='PODINFO_UI_MESSAGE', value=spec['ui']['message']))

    # Extract the value of PODINFO_CACHE_SERVER from the env list
    podinfo_cache_server_value = next((e['value'] for e in spec['env'] if e['name'] == 'PODINFO_CACHE_SERVER'), None)
    if podinfo_cache_server_value:
        env_vars.append(client.V1EnvVar(name='PODINFO_CACHE_SERVER', value=podinfo_cache_server_value))

    deployment = client.V1Deployment(
        metadata=client.V1ObjectMeta(name='podinfo'),
        spec=client.V1DeploymentSpec(
            replicas=spec['replicaCount'],
            selector=client.V1LabelSelector(
                match_labels={"app": "podinfo"}
            ),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": "podinfo"}),
                spec=client.V1PodSpec(
                    containers=[
                        client.V1Container(
                            name='podinfo',
                            image=f"{spec['image']['repository']}:{spec['image']['tag']}",
                            env=env_vars
                        )
                    ]
                )
            )
        )
    )
    try:
        apps_v1.create_namespaced_deployment(namespace, deployment)
    except ApiException as e:
        if e.status == 409:
            print("Deployment already exists, updating instead")
            update_podinfo_deployment(spec, namespace)
        else:
            raise



def delete_podinfo_deployment(namespace):
    apps_v1.delete_namespaced_deployment('podinfo', namespace)


def update_podinfo_deployment(spec, namespace, max_retries=3):
    for _ in range(max_retries):
        try:
            existing_deployment = apps_v1.read_namespaced_deployment('podinfo', namespace)
            existing_deployment.spec.replicas = spec['replicaCount']
            existing_deployment.spec.template.spec.containers[
                0].image = f"{spec['image']['repository']}:{spec['image']['tag']}"

            # Update all environment variables
            env_vars = [client.V1EnvVar(name=e['name'], value=e['value']) for e in spec['env']]
            env_vars.append(client.V1EnvVar(name='PODINFO_UI_COLOR', value=spec['ui']['color']))
            env_vars.append(client.V1EnvVar(name='PODINFO_UI_MESSAGE', value=spec['ui']['message']))

            existing_deployment.spec.template.spec.containers[0].env = env_vars

            apps_v1.replace_namespaced_deployment('podinfo', namespace, existing_deployment)
            return
        except ApiException as e:
            if e.status == 409:
                print("Conflict while updating deployment. Retrying...")
            else:
                raise


def handle_event(event_type, event_object):
    print(f"Handling event: {event_type}")  # Log the event type
    namespace = event_object['metadata']['namespace']
    spec = event_object['spec']

    if event_type == "ADDED":
        # Handle Redis secret
        if spec.get('redis', {}).get('enabled'):
            create_redis_secret(namespace)
        # Deploy podinfo application
        create_podinfo_deployment(spec, namespace)

    elif event_type == "MODIFIED":
        update_podinfo_deployment(spec, namespace)

    elif event_type == "DELETED":
        # Delete podinfo deployment
        delete_podinfo_deployment(namespace)


def main():
    resource_version = ""
    while True:
        stream = watch.Watch().stream(
            custom_api.list_cluster_custom_object,
            GROUP, VERSION, PLURAL,
            resource_version=resource_version
        )
        for event in stream:
            resource_version = event['object']['metadata']['resourceVersion']
            handle_event(event['type'], event['object'])


if __name__ == "__main__":
    main()
