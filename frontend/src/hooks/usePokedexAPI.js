import { useState, useCallback } from 'react';
import { sendMultimodalQuery } from '../services/api';

export const usePokedexAPI = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendQuery = useCallback(async ({ text, imageFile, audioBlob }) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendMultimodalQuery({ text, imageFile, audioBlob });
      return response;
    } catch (err) {
      const message = err.response?.data?.detail || 'Connection to the Pokédex network failed.';
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { sendQuery, isLoading, error };
};