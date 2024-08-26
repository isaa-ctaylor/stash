# stash
A minimal, open source pastebin.

## Deployment

### Building and Starting the Server with Docker Compose

To build and start the server using Docker Compose, follow these steps:

#### Prerequisites

Make sure you have the following installed on your machine:

- [Docker](https://docs.docker.com/get-docker/) (including Docker Engine and Docker CLI)
- [Docker Compose](https://docs.docker.com/compose/install/) (Docker Compose V2 is recommended)

#### Steps

1. **Clone the Repository**

   If you haven’t already cloned the repository, do so with the following command:

   ```bash
   git clone https://github.com/isaa-ctaylor/stash.git
   cd stash
   ```
2. **Navigate to the Root Directory**

    Ensure you are in the root directory of the repository where the docker-compose.yml file is located.

3. **Build and Start the Server**

    Use the following command to build the Docker images and start the server:

    ```bash
    docker compose up --build
    ```
    The --build flag forces Docker Compose to build images before starting the containers.
    This command will pull necessary images, build your application image, and start the services defined in your docker-compose.yml file.
4. **Verify the Server is Running**

    After running the command, Docker Compose will output logs from the containers. You can also verify the server is running by visiting http://localhost:8080 in your web browser.

5. **Stopping the Server**

    To stop and remove the containers, use:

    ```bash
    docker compose down
    ```
    This command will stop the running containers and remove them, along with any networks created by Docker Compose.

For more detailed configuration or troubleshooting, refer to the Docker Compose documentation.