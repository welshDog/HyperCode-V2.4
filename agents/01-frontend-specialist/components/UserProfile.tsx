
import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface User {
    id: string;
    name: string;
    email: string;
    avatar_url: string;
}

export const UserProfile = ({ userId }: { userId: string }) => {
    const [user, setUser] = useState<User | null>(null);

    useEffect(() => {
        fetch(`/api/user/${userId}`)
            .then(res => res.json())
            .then(data => setUser(data));
    }, [userId]);

    if (!user) return <div>Loading...</div>;

    return (
        <div className="p-4 border rounded shadow-md">
            <img src={user.avatar_url} alt={user.name} className="w-16 h-16 rounded-full" />
            <h2 className="text-xl font-bold">{user.name}</h2>
            <p className="text-gray-600">{user.email}</p>
        </div>
    );
};
