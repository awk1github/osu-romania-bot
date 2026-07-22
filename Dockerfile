FROM python:3.14.3

# Set the working directory
WORKDIR /app

# Copy the requirements file first (better for caching)
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your friend's code
COPY . .

EXPOSE 8080

# Start the bot
CMD ["sh", "-c", "python init_db.py && python main.py"]
