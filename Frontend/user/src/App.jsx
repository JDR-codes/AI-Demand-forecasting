export default function App() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-700 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-2xl p-10 max-w-md w-full text-center">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">
          🎉 Tailwind CSS is Working!
        </h1>

        <p className="text-gray-600 mb-8">
          Your React + Vite + Tailwind CSS setup is successful.
        </p>

        <button className="bg-blue-600 hover:bg-blue-700 text-white font-semibold px-6 py-3 rounded-lg transition duration-300">
          Click Me
        </button>
      </div>
    </div>
  );
}