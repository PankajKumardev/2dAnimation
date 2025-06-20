import express from 'express';
import axios from 'axios';
import cors from 'cors';
const app = express();

app.use(express.json());
app.use(cors());

app.post('/generate', async (req, res) => {
  try {
    const response = await axios.post('http://localhost:8000/generate', {
      prompt: req.body.prompt,
      quality : req.body.quality || '720p',
    });
    res.status(200).json(response.data);
    return;
  } catch (e) {
    res.status(500).json({ error: 'Error generating response', detail: e });
    return;
  }
});

app.listen(3000, () => {
  console.log('Server is running on port 3000');
});
