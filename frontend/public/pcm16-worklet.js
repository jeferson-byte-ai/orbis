class Pcm16WorkletProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._inputRate = sampleRate; // typically 48000
    this._targetRate = 16000;
    this._ratio = this._inputRate / this._targetRate;
  }

  static get parameterDescriptors() { return []; }

  _downsample(input) {
    if (this._targetRate >= this._inputRate) {
      return input.slice(0);
    }
    const sampleRateRatio = this._ratio;
    const newLength = Math.round(input.length / sampleRateRatio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < input.length; i++) {
        accum += input[i];
        count++;
      }
      result[offsetResult] = count > 0 ? accum / count : 0;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  _floatTo16BitPCM(buffer) {
    const output = new Int16Array(buffer.length);
    for (let i = 0; i < buffer.length; i++) {
      let s = buffer[i];
      if (s > 1) s = 1;
      else if (s < -1) s = -1;
      output[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return output;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) {
      return true;
    }
    const channelData = input[0];
    if (!channelData || channelData.length === 0) {
      return true;
    }
    const down = this._downsample(channelData);
    if (down && down.length > 0) {
      const pcm16 = this._floatTo16BitPCM(down);
      this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    }
    return true;
  }
}

registerProcessor('pcm16-worklet', Pcm16WorkletProcessor);
